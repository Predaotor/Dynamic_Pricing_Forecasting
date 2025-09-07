from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from typing import List, Optional
from app.core.db import get_async_db
from app.models.sales import SalesDaily, RawSales
from app.models.product import Product
from app.models.org import Organization
from pydantic import BaseModel

router = APIRouter()

class DashboardStats(BaseModel):
    total_sales: int
    total_revenue: float
    total_products: int
    total_organizations: int
    pending_etl: int
    processed_etl: int
    failed_etl: int

class SalesTrend(BaseModel):
    date: str
    units_sold: int
    revenue: float

class TopProduct(BaseModel):
    product_id: str
    product_name: str
    total_units: int
    total_revenue: float
    avg_price: float

@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: AsyncSession = Depends(get_async_db)):
    """Get dashboard key performance indicators"""
    try:
        # Get sales stats
        sales_result = await db.execute(
            select(
                func.sum(SalesDaily.units_sold).label("total_sales"),
                func.sum(SalesDaily.revenue).label("total_revenue")
            )
        )
        sales_row = sales_result.first()
        total_sales = sales_row.total_sales or 0
        total_revenue = float(sales_row.total_revenue or 0)

        # Get product and org counts
        products_result = await db.execute(select(func.count(Product.id)))
        total_products = products_result.scalar() or 0

        orgs_result = await db.execute(select(func.count(Organization.id)))
        total_organizations = orgs_result.scalar() or 0

        # Get ETL status
        etl_result = await db.execute(
            select(
                func.count(RawSales.raw_id).filter(RawSales.status == "pending").label("pending"),
                func.count(RawSales.raw_id).filter(RawSales.status == "processed").label("processed"),
                func.count(RawSales.raw_id).filter(RawSales.status == "failed").label("failed")
            )
        )
        etl_row = etl_result.first()
        pending_etl = etl_row.pending or 0
        processed_etl = etl_row.processed or 0
        failed_etl = etl_row.failed or 0

        return DashboardStats(
            total_sales=total_sales,
            total_revenue=total_revenue,
            total_products=total_products,
            total_organizations=total_organizations,
            pending_etl=pending_etl,
            processed_etl=processed_etl,
            failed_etl=failed_etl
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching dashboard stats: {str(e)}")

@router.get("/dashboard/sales-trend", response_model=List[SalesTrend])
async def get_sales_trend(
    days: int = 30,
    db: AsyncSession = Depends(get_async_db)
):
    """Get sales trend data for the last N days"""
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        result = await db.execute(
            select(
                SalesDaily.date,
                func.sum(SalesDaily.units_sold).label("units_sold"),
                func.sum(SalesDaily.revenue).label("revenue")
            )
            .filter(SalesDaily.date >= start_date)
            .filter(SalesDaily.date <= end_date)
            .group_by(SalesDaily.date)
            .order_by(SalesDaily.date)
        )

        trends = []
        for row in result:
            trends.append(SalesTrend(
                date=row.date.isoformat(),
                units_sold=row.units_sold or 0,
                revenue=float(row.revenue or 0)
            ))

        return trends
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching sales trend: {str(e)}")

@router.get("/dashboard/top-products", response_model=List[TopProduct])
async def get_top_products(
    limit: int = 10,
    db: AsyncSession = Depends(get_async_db)
):
    """Get top selling products by revenue"""
    try:
        result = await db.execute(
            select(
                Product.id,
                Product.name,
                func.sum(SalesDaily.units_sold).label("total_units"),
                func.sum(SalesDaily.revenue).label("total_revenue"),
                func.avg(SalesDaily.price).label("avg_price")
            )
            .join(SalesDaily, Product.id == SalesDaily.product_id)
            .group_by(Product.id, Product.name)
            .order_by(desc(func.sum(SalesDaily.revenue)))
            .limit(limit)
        )

        products = []
        for row in result:
            products.append(TopProduct(
                product_id=str(row.id),
                product_name=row.name,
                total_units=row.total_units or 0,
                total_revenue=float(row.total_revenue or 0),
                avg_price=float(row.avg_price or 0)
            ))

        return products
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching top products: {str(e)}")

@router.get("/dashboard/raw-sales", response_model=List[dict])
async def get_raw_sales(
    limit: int = 50,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db)
):
    """Get raw sales data for the ETL monitor"""
    try:
        query = select(RawSales).order_by(desc(RawSales.uploaded_at)).limit(limit)
        
        if status:
            query = query.filter(RawSales.status == status)

        result = await db.execute(query)
        raw_sales = result.scalars().all()

        return [
            {
                "raw_id": str(raw.raw_id),
                "source": raw.source,
                "status": raw.status,
                "uploaded_at": raw.uploaded_at.isoformat() if raw.uploaded_at else None,
                "error_message": raw.error_message,
                "raw_json": raw.raw_json
            }
            for raw in raw_sales
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching raw sales: {str(e)}")
