from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.core.db import Base
from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

class Product(Base):
    """
    Product entity representing an item for sale, belonging to an organization.
    Fields:
        - id: UUID primary key
        - org_id: UUID foreign key to organizations
        - sku: Stock Keeping Unit identifier
        - name: Product name
        - currency: Currency code (e.g., USD)
        - created_at: Timestamp of creation
    """
    __tablename__ = "products"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    sku = Column(String, nullable=False)
    name = Column(String, nullable=False)
    currency = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    sales = relationship("SalesDaily", back_populates="product", cascade="all, delete-orphan")
    costs = relationship("Cost", back_populates="product", cascade="all, delete-orphan")
    forecasts = relationship("Forecast", back_populates="product", cascade="all, delete-orphan")
    elasticity_estimates = relationship("ElasticityEstimate", back_populates="product", cascade="all, delete-orphan")
    price_recommendations = relationship("PriceRecommendation", back_populates="product", cascade="all, delete-orphan")
