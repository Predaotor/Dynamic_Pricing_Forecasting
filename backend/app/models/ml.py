from sqlalchemy import Column, String, DateTime, Date, Numeric, ForeignKey, BigInteger, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.core.db import Base
from datetime import datetime
import uuid

class ModelRun(Base):
    __tablename__ = "model_runs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    model_name = Column(String, nullable=False)
    model_version = Column(String, nullable=False)
    params = Column(JSON, nullable=True)
    started_at = Column(DateTime, default=datetime.now, nullable=False)
    finished_at = Column(DateTime, nullable=True)

class Forecast(Base):
    __tablename__ = "forecasts"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    model_run_id = Column(UUID(as_uuid=True), ForeignKey("model_runs.id"), nullable=False)
    target_date = Column(Date, nullable=False)
    predicted_units = Column(Numeric, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

class ElasticityEstimate(Base):
    __tablename__ = "elasticity_estimates"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    model_run_id = Column(UUID(as_uuid=True), ForeignKey("model_runs.id"), nullable=False)
    window_start = Column(Date, nullable=False)
    window_end = Column(Date, nullable=False)
    elasticity = Column(Numeric, nullable=False)
    r2 = Column(Numeric, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

class PriceRecommendation(Base):
    __tablename__ = "price_recommendations"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    model_run_id = Column(UUID(as_uuid=True), ForeignKey("model_runs.id"), nullable=False)
    target_date = Column(Date, nullable=False)
    objective = Column(String, nullable=False)
    suggested_price = Column(Numeric, nullable=False)
    expected_units = Column(Numeric, nullable=False)
    expected_revenue = Column(Numeric, nullable=False)
    expected_profit = Column(Numeric, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
