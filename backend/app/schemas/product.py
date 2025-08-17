from pydantic import BaseModel, Field
from typing import Optional, Any
from uuid import UUID
from datetime import datetime, date

class RawSalesSchema(BaseModel):
    """
    Schema for staging raw sales data uploads.
    """
    raw_id: Optional[int]
    uploaded_at: Optional[datetime]
    source: Optional[str]
    raw_json: Any
    status: Optional[str]

class SalesDailySchema(BaseModel):
    """
    Schema for standardized daily sales data after ETL from RawSales.
    """
    id: Optional[int]
    product_id: UUID
    date: date
    units_sold: int
    price: float
    revenue: float
    created_at: Optional[datetime]

class CostSchema(BaseModel):
    """
    Schema for daily unit cost for each product.
    """
    id: Optional[int]
    product_id: UUID
    date: date
    unit_cost: float
    created_at: Optional[datetime]
