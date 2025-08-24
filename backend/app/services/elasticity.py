"""
Elasticity Service - Estimate price elasticity using log-log OLS regression.
Following Instructions.md 5.1: Fit log–log OLS; store elasticity and r2 with new model_runs row.
"""

import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from app.models.sales import SalesDaily
from app.models.ml import ModelRun, ElasticityEstimate
from app.models.product import Product
from datetime import date, timedelta
from typing import Optional, Tuple
from uuid import uuid4
import logging

logger = logging.getLogger(__name__)


async def estimate_elasticity(
    session: AsyncSession,
    product_id: str,
    window_days: int = 90,
    min_price_variance: float = 0.1,
    min_r2_threshold: float = 0.2
) -> dict:
    """
    Estimate price elasticity for a product over a rolling window.
    
    Args:
        session: Async database session
        product_id: Product UUID to analyze
        window_days: Number of days to look back
        min_price_variance: Minimum price coefficient of variation for confidence
        min_r2_threshold: Minimum R² for confidence
        
    Returns:
        dict with elasticity, r2, confidence, and model_run_id
    """
    
    # Calculate date range
    end_date = date.today()
    start_date = end_date - timedelta(days=window_days)
    
    # Query sales data for the product in the window
    result = await session.execute(
        select(SalesDaily.date, SalesDaily.price, SalesDaily.units_sold)
        .where(
            SalesDaily.product_id == product_id,
            SalesDaily.date >= start_date,
            SalesDaily.date <= end_date
        )
        .order_by(SalesDaily.date)
    )
    
    sales_data = result.fetchall()
    
    if len(sales_data) < 10:  # Need minimum data points
        raise ValueError(f"Insufficient data: only {len(sales_data)} sales records found")
    
    # Convert to DataFrame for analysis
    df = pd.DataFrame(sales_data, columns=['date', 'price', 'units_sold'])
    
    # Calculate price variance
    df['price']=df['price'].astype(float)
    price_cv = df['price'].std() / df['price'].mean()
    
    if price_cv < min_price_variance:
        logger.warning(f"Low price variance ({price_cv:.3f}) for product {product_id}")
        confidence = "low_price_variance"
    else:
        confidence = "high"
    
    # Fit log-log OLS: ln(q) = a + b*ln(p)
    # where b is the elasticity
    df['ln_price'] = np.log(df['price'])
    df['ln_quantity'] = np.log(df['units_sold'])
    
    # Remove any infinite/NaN values
    df = df.replace([np.inf, -np.inf], np.nan).dropna()
    
    if len(df) < 5:
        raise ValueError("Insufficient valid data points after cleaning")
    
    # Simple OLS regression
    X = df['ln_price'].values.reshape(-1, 1)
    y = df['ln_quantity'].values
    
    # Add constant term
    X_with_const = np.column_stack([np.ones(len(X)), X])
    
    try:
        # Solve: (X'X)^(-1) * X'y
        beta = np.linalg.inv(X_with_const.T @ X_with_const) @ X_with_const.T @ y
        intercept, elasticity = beta
        
        # Calculate R²
        y_pred = X_with_const @ beta
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        # Check R² threshold
        if r2 < min_r2_threshold:
            confidence = "low_r2"
            logger.warning(f"Low R² ({r2:.3f}) for product {product_id}")
        
        # Validate elasticity sign (should typically be negative)
        if elasticity > 0:
            logger.warning(f"Positive elasticity ({elasticity:.3f}) for product {product_id}")
        
        # Store results
        model_run = ModelRun(
            id=uuid4(),
            model_name="log_log_ols",
            model_version="1.0",
            params={
                "window_days": window_days,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "data_points": len(df),
                "price_cv": float(price_cv),
                "min_price_variance": min_price_variance,
                "min_r2_threshold": min_r2_threshold,
                "confidence": confidence
            }
        )
        session.add(model_run)
        await session.flush()
        
        # Store elasticity estimate
        elasticity_estimate = ElasticityEstimate(
            product_id=product_id,
            model_run_id=model_run.id,
            window_start=start_date,
            window_end=end_date,
            elasticity=float(elasticity),
            r2=float(r2)
        )
        session.add(elasticity_estimate)
        
        await session.commit()
        
        return {
            "elasticity": float(elasticity),
            "r2": float(r2),
            "confidence": confidence,
            "model_run_id": str(model_run.id),
            "data_points": len(df),
            "price_cv": float(price_cv),
            "window_days": window_days
        }
        
    except np.linalg.LinAlgError as e:
        logger.error(f"Linear algebra error in elasticity calculation: {e}")
        raise ValueError("Failed to calculate elasticity: insufficient price variation")
    except Exception as e:
        logger.error(f"Unexpected error in elasticity calculation: {e}")
        raise
