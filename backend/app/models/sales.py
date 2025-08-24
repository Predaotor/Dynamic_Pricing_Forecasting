from sqlalchemy import Column, Date, Integer, Numeric, DateTime, ForeignKey, BigInteger, String, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from app.core.db import Base
from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

class RawSales(Base):
    """
    Staging table for raw sales data uploads. Stores the original row as JSON, plus metadata.
    Fields:
        - raw_id: BigInteger primary key
        - uploaded_at: Timestamp of upload
        - source: Source identifier (client, file, etc.)
        - raw_json: Original row as JSON
        - status: ETL status (pending, processed, error)
        - error_message: Optional error text when processing fails
    """
    __tablename__ = "raw_sales"
    raw_id = Column(BigInteger, primary_key=True, autoincrement=True)
    uploaded_at = Column(DateTime, server_default=func.now(), nullable=False)
    source = Column(String, nullable=True)
    raw_json = Column(JSON, nullable=False)
    status = Column(String, default="pending", nullable=False)
    error_message = Column(String, nullable=True)

class SalesDaily(Base):
    """
    Standardized daily sales data after ETL from RawSales.
    Fields:
        - id: BigInteger primary key
        - product_id: UUID foreign key to products
        - date: Date of sale
        - units_sold: Number of units sold
        - price: Sale price per unit
        - revenue: Total revenue
        - created_at: Timestamp of creation
    """
    __tablename__ = "sales_daily"
    __table_args__ = (
        UniqueConstraint("product_id", "date", name="uq_sales_product_date"),
    )
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    date = Column(Date, nullable=False)
    units_sold = Column(Integer, nullable=False)
    price = Column(Numeric, nullable=False)
    revenue = Column(Numeric, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    product = relationship("Product", back_populates="sales")

class Cost(Base):
    """
    Daily unit cost for each product.
    Fields:
        - id: BigInteger primary key
        - product_id: UUID foreign key to products
        - date: Date of cost
        - unit_cost: Cost per unit
        - created_at: Timestamp of creation
    """
    __tablename__ = "costs"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    date = Column(Date, nullable=False)
    unit_cost = Column(Numeric, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    product = relationship("Product", back_populates="costs")
