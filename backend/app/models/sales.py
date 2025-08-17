from sqlalchemy import Column, Date, Integer, Numeric, DateTime, ForeignKey, BigInteger, String, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.core.db import Base
from datetime import datetime

class RawSales(Base):
    """
    Staging table for raw sales data uploads. Stores the original row as JSON, plus metadata.
    """
    __tablename__ = "raw_sales"
    raw_id = Column(BigInteger, primary_key=True, autoincrement=True)
    uploaded_at = Column(DateTime, default=datetime.now, nullable=False)
    source = Column(String, nullable=True)
    raw_json = Column(JSON, nullable=False)
    status = Column(String, default="pending", nullable=False)

class SalesDaily(Base):
    """
    Standardized daily sales data after ETL from RawSales.
    """
    __tablename__ = "sales_daily"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    date = Column(Date, nullable=False)
    units_sold = Column(Integer, nullable=False)
    price = Column(Numeric, nullable=False)
    revenue = Column(Numeric, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

class Cost(Base):
    """
    Daily unit cost for each product.
    """
    __tablename__ = "costs"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    date = Column(Date, nullable=False)
    unit_cost = Column(Numeric, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
