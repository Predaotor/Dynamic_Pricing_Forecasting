"""
ML Router - Endpoints for machine learning operations.
Following Instructions.md 2.5: ML endpoints for elasticity, forecasting, and pricing.
"""

from fastapi import APIRouter, Query, HTTPException
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.db import DATABASE_URL
import logging
from typing import Optional
from datetime import date

logger = logging.getLogger(__name__)

router = APIRouter()


def get_async_session():
    """Create async session for ML operations."""
    try:
        # Convert sync URL to async URL
        
        async_url = DATABASE_URL.set(drivername="postgresql+asyncpg")
        
        logger.info(f"Creating async engine with URL: {async_url}")
        engine = create_async_engine(async_url, future=True, echo=False)
        AsyncLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        return AsyncLocal, engine
    except Exception as e:
        logger.error(f"Failed to create async session: {e}")
        raise


@router.post("/ml/estimate-elasticity")
async def estimate_elasticity_endpoint(
    product_id: str = Query(..., description="Product UUID"),
    window_days: int = Query(90, description="Days to look back for elasticity calculation"),
    min_price_variance: float = Query(0.1, description="Minimum price coefficient of variation"),
    min_r2_threshold: float = Query(0.2, description="Minimum R² threshold")
):
    """Estimate price elasticity for a product using log-log OLS regression."""
    try:
        from app.services.elasticity import estimate_elasticity
    except ImportError as e:
        logger.error(f"Failed to import elasticity service: {e}")
        raise HTTPException(status_code=500, detail="Elasticity service not available")
    
    session_factory, engine = get_async_session()
    
    try:
        async with session_factory() as async_session:
            result = await estimate_elasticity(
                session=async_session,
                product_id=product_id,
                window_days=window_days,
                min_price_variance=min_price_variance,
                min_r2_threshold=min_r2_threshold
            )
            return result
    except ValueError as e:
        logger.warning(f"Validation error in elasticity estimation: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in elasticity estimation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Elasticity estimation failed: {str(e)}")
    finally:
        await engine.dispose()


@router.post("/ml/run-forecast")
async def run_forecast_endpoint(
    product_id: str = Query(..., description="Product UUID"),
    horizon: int = Query(30, description="Number of days to forecast"),
    min_data_days: int = Query(60, description="Minimum days of data required"),
    test_days: int = Query(14, description="Days to use for testing/evaluation")
):
    """Run demand forecasting for a product using LightGBM."""
    try:
        from app.services.forecasting import run_forecast
    except ImportError as e:
        logger.error(f"Failed to import forecasting service: {e}")
        raise HTTPException(status_code=500, detail="Forecasting service not available")
    
    session_factory, engine = get_async_session()
    
    try:
        async with session_factory() as async_session:
            result = await run_forecast(
                session=async_session,
                product_id=product_id,
                horizon=horizon,
                min_data_days=min_data_days,
                test_days=test_days
            )
            return result
    except ValueError as e:
        logger.warning(f"Validation error in forecasting: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ImportError as e:
        logger.error(f"LightGBM import error: {e}")
        raise HTTPException(status_code=500, detail="LightGBM not available. Install with: pip install lightgbm")
    except Exception as e:
        logger.error(f"Unexpected error in forecasting: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Forecasting failed: {str(e)}")
    finally:
        await engine.dispose()


@router.post("/ml/recommend-prices")
async def recommend_prices_endpoint(
    product_id: str = Query(..., description="Product UUID"),
    objective: str = Query("revenue", description="Optimization objective: 'revenue' or 'profit'"),
    pmin: Optional[float] = Query(None, description="Minimum price (defaults to 0.5 * baseline)"),
    pmax: Optional[float] = Query(None, description="Maximum price (defaults to 1.5 * baseline)"),
    horizon: int = Query(30, description="Number of days to recommend prices for")
):
    """Recommend optimal prices for a product using elasticity and demand curves."""
    try:
        from app.services.pricing import recommend_prices
    except ImportError as e:
        logger.error(f"Failed to import pricing service: {e}")
        raise HTTPException(status_code=500, detail="Pricing service not available")
    
    session_factory, engine = get_async_session()
    
    try:
        async with session_factory() as async_session:
            result = await recommend_prices(
                session=async_session,
                product_id=product_id,
                objective=objective,
                pmin=pmin,
                pmax=pmax,
                horizon=horizon
            )
            return result
    except ValueError as e:
        logger.warning(f"Validation error in price recommendation: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in price recommendation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Price recommendation failed: {str(e)}")
    finally:
        await engine.dispose()


@router.get("/products/{product_id}/forecasts")
async def get_product_forecasts(
    product_id: str,
    from_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)")
):
    """Get forecasts for a specific product within a date range."""
    try:
        from app.services.forecasting import get_forecasts
    except ImportError as e:
        logger.error(f"Failed to import forecasting service: {e}")
        raise HTTPException(status_code=500, detail="Forecasting service not available")
    
    session_factory, engine = get_async_session()
    
    try:
        async with session_factory() as async_session:
            forecasts = await get_forecasts(
                session=async_session,
                product_id=product_id,
                from_date=from_date,
                to_date=to_date
            )
            return {"forecasts": forecasts}
    except Exception as e:
        logger.error(f"Failed to retrieve forecasts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve forecasts: {str(e)}")
    finally:
        await engine.dispose()


@router.get("/products/{product_id}/recommendations")
async def get_product_recommendations(
    product_id: str,
    from_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    objective: Optional[str] = Query(None, description="Filter by objective: 'revenue' or 'profit'")
):
    """Get price recommendations for a specific product within a date range."""
    try:
        from app.services.pricing import get_price_recommendations
    except ImportError as e:
        logger.error(f"Failed to import pricing service: {e}")
        raise HTTPException(status_code=500, detail="Pricing service not available")
    
    session_factory, engine = get_async_session()
    
    try:
        async with session_factory() as async_session:
            recommendations = await get_price_recommendations(
                session=async_session,
                product_id=product_id,
                from_date=from_date,
                to_date=to_date,
                objective=objective
            )
            return {"recommendations": recommendations}
    except Exception as e:
        logger.error(f"Failed to retrieve recommendations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve recommendations: {str(e)}")
    finally:
        await engine.dispose()
