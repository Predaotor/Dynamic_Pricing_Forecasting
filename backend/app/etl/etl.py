# backend/app/etl/etl.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.dialects.postgresql import insert
from app.models.sales import RawSales, SalesDaily
from app.models.product import Product
from datetime import date, datetime, timezone
from typing import Optional
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel, ValidationError, field_validator
import json
import logging

logger = logging.getLogger(__name__)


class SalesRow(BaseModel):
    """Protective schema for validating and normalizing sales data."""
    product_id: UUID
    date: date  # align with SalesDaily.date if it's a DATE column
    units_sold: int
    price: Decimal
    revenue: Optional[Decimal] = None

    @field_validator("units_sold")
    def non_negative_units(cls, v):
        if v < 0:
            raise ValueError("units_sold cannot be negative")
        return v

    @field_validator("price")
    def non_negative_price(cls, v):
        if v < 0:
            raise ValueError("price cannot be negative")
        return v

    def calculate_revenue(self):
        if self.revenue is None:
            self.revenue = self.units_sold * self.price


async def ensure_product_exists(session: AsyncSession, product_id: UUID) -> bool:
    """Ensure product exists, create minimal record if missing."""
    result = await session.execute(
        select(Product).where(Product.id == product_id)
    )
    if result.scalar_one_or_none():
        return True
    
    # Create minimal product if missing (following Instructions.md 2.4)
    try:
        # First, try to find any existing organization, or create a default one
        from app.models.org import Organization
        
        org_result = await session.execute(select(Organization).limit(1))
        org = org_result.scalar_one_or_none()
        
        if not org:
            # Create a default organization for auto-created products
            org = Organization(name="Default Organization")
            session.add(org)
            await session.flush()
            logger.info(f"Created default organization {org.id}")
        
        product = Product(
            id=product_id,  # Use the provided UUID
            org_id=org.id,  # Use the found/created org
            sku=f"AUTO-{product_id.hex[:8]}",
            name=f"Auto-created Product {product_id.hex[:8]}",
            currency="USD"  # Default currency
        )
        session.add(product)
        await session.flush()  # Get the ID assigned
        logger.warning(f"Created missing product {product_id} for org {org.id}")
        return True
    except Exception as e:
        logger.error(f"Failed to create product {product_id}: {e}")
        return False


async def run_etl(session: AsyncSession, batch_size: int = 500):
    """
    Extract-Transform-Load pipeline with improvements:
    1. Extract pending rows in batches (row-locking to avoid concurrency issues)
    2. Transform → validate & normalize (Pydantic schema)
    3. Load → ensure products exist, then upsert sales
    4. Update RawSales status (processed/failed + error message)
    """

    while True:
        # 1) Extract with SKIP LOCKED to avoid duplicate work if multiple workers
        result = await session.execute(
            select(RawSales)
            .where(RawSales.status == "pending")
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
        raw_rows = result.scalars().all()

        if not raw_rows:
            logger.info("No more raw sales to process.")
            break

        for raw in raw_rows:
            try:
                # Handle JSON field
                data = raw.raw_json
                if isinstance(data, str):
                    data = json.loads(data)

                # 2) Transform: explicit defaults (no `or` to avoid overriding 0)
                normalized = {
                    "product_id": (
                        data["product_id"] if "product_id" in data else data.get("productID")
                    ),
                    "date": (
                        datetime.fromisoformat(data["date"]).date()
                        if "date" in data and data["date"]
                        else datetime.now(timezone.utc).date()
                    ),
                    "units_sold": (
                        data["units_sold"] if "units_sold" in data else data.get("quantity", 0)
                    ),
                    "price": (
                        Decimal(str(data["price"]))
                        if "price" in data
                        else Decimal(str(data.get("unit_price", "0")))
                    ),
                    "revenue": (
                        Decimal(str(data["revenue"])) if "revenue" in data and data["revenue"] else None
                    ),
                }

                # Validate with Pydantic (will coerce types + enforce rules)
                sales_row = SalesRow(**normalized)
                sales_row.calculate_revenue()

                # 3) Load → ensure product exists, then upsert sales
                if not await ensure_product_exists(session, sales_row.product_id):
                    raise Exception(f"Failed to ensure product {sales_row.product_id} exists")

                stmt = insert(SalesDaily.__table__).values(
                    product_id=sales_row.product_id,
                    date=sales_row.date,
                    units_sold=sales_row.units_sold,
                    price=sales_row.price,
                    revenue=sales_row.revenue,
                    created_at=func.now(),
                ).on_conflict_do_update(
                    index_elements=[SalesDaily.product_id, SalesDaily.date],
                    set_={
                        "units_sold": sales_row.units_sold,
                        "price": sales_row.price,
                        "revenue": sales_row.revenue,
                        "created_at": func.now(),
                    }
                )
                await session.execute(stmt)

                # 4) Mark staging row as processed
                await session.execute(
                    update(RawSales)
                    .where(RawSales.raw_id == raw.raw_id)
                    .values(status="processed", error_message=None)
                )

            except ValidationError as e:
                logger.error(f"Validation failed for raw_id={raw.raw_id}: {e}")
                await session.execute(
                    update(RawSales)
                    .where(RawSales.raw_id == raw.raw_id)
                    .values(status="failed", error_message=str(e))
                )

            except Exception as e:
                logger.exception(f"Unexpected ETL error for raw_id={raw.raw_id}: {e}")
                await session.execute(
                    update(RawSales)
                    .where(RawSales.raw_id == raw.raw_id)
                    .values(status="failed", error_message=str(e))
                )

        # Commit after each batch
        await session.commit()

    logger.info("ETL pipeline completed.")
