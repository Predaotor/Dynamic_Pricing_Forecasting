from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime, date

class ForecastSchema(BaseModel):
    """
    Schema for forecasted demand per product.
    """
    id: Optional[int]
    product_id: UUID
    model_run_id: UUID
    target_date: date
    predicted_units: float
    created_at: Optional[datetime]

class ElasticityEstimateSchema(BaseModel):
    """
    Schema for price elasticity estimates per product.
    """
    id: Optional[int]
    product_id: UUID
    model_run_id: UUID
    window_start: date
    window_end: date
    elasticity: float
    r2: float
    created_at: Optional[datetime]

class PriceRecommendationSchema(BaseModel):
    """
    Schema for price recommendations per product and date.
    """
    id: Optional[int]
    product_id: UUID
    model_run_id: UUID
    target_date: date
    objective: str
    suggested_price: float
    expected_units: float
    expected_revenue: float
    expected_profit: float
    created_at: Optional[datetime]
