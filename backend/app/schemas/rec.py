from pydantic import BaseModel
from typing import Optional, Any
from uuid import UUID
from datetime import datetime

class ProductSchema(BaseModel):
    """
    Schema for product entity.
    """
    id: Optional[UUID]
    org_id: UUID
    sku: str
    name: str
    currency: str
    created_at: Optional[datetime]

class ModelRunSchema(BaseModel):
    """
    Schema for model run metadata.
    """
    id: Optional[UUID]
    model_name: str
    model_version: str
    params: Optional[Any]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
