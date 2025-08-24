"""
Forecasting Service - Forecast demand using LightGBM with engineered features.
Following Instructions.md 5.2: Build feature frame from sales (lags, MAs, calendar, price).
Train LightGBM; evaluate on last k days; record metrics.
"""

import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.sales import SalesDaily
from app.models.ml import ModelRun, Forecast
from datetime import date, timedelta
from typing import List, Optional
from uuid import uuid4
import logging

logger = logging.getLogger(__name__)

# Note: LightGBM import is commented out for now - you'll need to install it
# import lightgbm as lgb

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    logger.warning("LightGBM not available. Install with: pip install lightgbm")


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Engineer features for forecasting: lags, moving averages, calendar features.
    
    Args:
        df: DataFrame with columns ['date', 'units_sold', 'price']
        
    Returns:
        DataFrame with engineered features
    """
    df = df.copy()
    
    # Sort by date
    df = df.sort_values('date').reset_index(drop=True)
    
    # Calendar features
    df['day_of_week'] = df['date'].dt.dayofweek
    df['month'] = df['date'].dt.month
    df['day_of_month'] = df['date'].dt.day
    
    # Lag features (1, 7, 14, 28 days)
    for lag in [1, 7, 14, 28]:
        df[f'units_sold_lag_{lag}'] = df['units_sold'].shift(lag)
        df[f'price_lag_{lag}'] = df['price'].shift(lag)
    
    # Moving averages (7, 14, 28 days)
    for window in [7, 14, 28]:
        df[f'units_sold_ma_{window}'] = df['units_sold'].rolling(window=window, min_periods=1).mean()
        df[f'price_ma_{window}'] = df['price'].rolling(window=window, min_periods=1).mean()
    
    # Price change features
    df['price_change'] = df['price'].pct_change()
    df['price_change_lag_1'] = df['price_change'].shift(1)
    
    # Remove rows with NaN values (from lag calculations)
    df = df.dropna()
    
    return df


async def run_forecast(
    session: AsyncSession,
    product_id: str,
    horizon: int = 30,
    min_data_days: int = 60,
    test_days: int = 14
) -> dict:
    """
    Run demand forecasting for a product.
    
    Args:
        session: Async database session
        product_id: Product UUID to forecast
        horizon: Number of days to forecast
        min_data_days: Minimum days of data required
        test_days: Days to use for testing/evaluation
        
    Returns:
        dict with forecast results and model metrics
    """
    
    if not LIGHTGBM_AVAILABLE:
        raise ImportError("LightGBM not available. Install with: pip install lightgbm")
    
    # Query historical sales data
    result = await session.execute(
        select(SalesDaily.date, SalesDaily.units_sold, SalesDaily.price)
        .where(SalesDaily.product_id == product_id)
        .order_by(SalesDaily.date)
    )
    
    sales_data = result.fetchall()
    
    if len(sales_data) < min_data_days:
        raise ValueError(f"Insufficient data: only {len(sales_data)} days found, need {min_data_days}")
    
    # Convert to DataFrame
    df = pd.DataFrame(sales_data, columns=['date', 'units_sold', 'price'])
    df['date'] = pd.to_datetime(df['date'])
    
   
    # Engineer features
    df_features = engineer_features(df)
    
    for col in df_features.columns:
        if col not in ['date', "units_sold"]:
            df_features[col]=pd.to_numeric(df_features[col], errors="coerce")
    
    if len(df_features) < min_data_days:
        raise ValueError(f"Insufficient data after feature engineering: {len(df_features)} rows")
    
    # Split into train/test
    split_idx = len(df_features) - test_days
    train_df = df_features.iloc[:split_idx]
    test_df = df_features.iloc[split_idx:]
    
    # Feature columns (exclude target and date)
    feature_cols = [col for col in df_features.columns 
                    if col not in ['date', 'units_sold']]
    
    X_train = train_df[feature_cols]
    y_train = train_df['units_sold']
    X_test = test_df[feature_cols]
    y_test = test_df['units_sold']
    
    # Train LightGBM model
    model = lgb.LGBMRegressor(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=6,
        random_state=42,
        verbose=-1
    )
    
    model.fit(X_train, y_train)
    
    # Evaluate on test set
    y_pred_test = model.predict(X_test)
    
    # Calculate MAPE
    mape = np.mean(np.abs((y_test - y_pred_test) / y_test)) * 100
    
    # Generate future predictions
    last_date = df_features['date'].max()
    future_dates = [last_date + timedelta(days=i+1) for i in range(horizon)]
    
    # Create future feature matrix (using last known values)
    last_row = df_features.iloc[-1]
    future_features = []
    
    for future_date in future_dates:
        # Create feature row for future date
        future_row = last_row.copy()
        future_row['date'] = future_date
        
        # Update calendar features
        future_row['day_of_week'] = future_date.dayofweek
        future_row['month'] = future_date.month
        future_row['day_of_month'] = future_date.day
        
        # For now, use last known values for lag/MA features
        # In production, you'd want to update these as you predict forward
        future_features.append(future_row[feature_cols].values)
    
    X_future = np.array(future_features)
    future_predictions = model.predict(X_future)
    
    # Store model run
    model_run = ModelRun(
        id=uuid4(),
        model_name="lightgbm_forecast",
        model_version="1.0",
        params={
            "horizon": horizon,
            "min_data_days": min_data_days,
            "test_days": test_days,
            "feature_count": len(feature_cols),
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "mape": float(mape)
        }
    )
    session.add(model_run)
    await session.flush()
    
    # Store forecasts
    forecasts = []
    for i, (future_date, prediction) in enumerate(zip(future_dates, future_predictions)):
        forecast = Forecast(
            product_id=product_id,
            model_run_id=model_run.id,
            target_date=future_date.date(),
            predicted_units=float(max(0, prediction))  # Ensure non-negative
        )
        forecasts.append(forecast)
    
    session.add_all(forecasts)
    await session.commit()
    
    return {
        "model_run_id": str(model_run.id),
        "horizon": horizon,
        "mape": float(mape),
        "forecasts": [
            {
                "date": f.date().isoformat(),
                "predicted_units": float(pred)
            }
            for f, pred in zip(future_dates, future_predictions)
        ],
        "feature_importance": {
            col: int(imp) for col, imp in zip(feature_cols, model.feature_importances_)
        }
    }


async def get_forecasts(
    session: AsyncSession,
    product_id: str,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None
) -> List[dict]:
    """
    Retrieve forecasts for a product within a date range.
    
    Args:
        session: Async database session
        product_id: Product UUID
        from_date: Start date (inclusive)
        to_date: End date (inclusive)
        
    Returns:
        List of forecast records
    """
    query = select(Forecast).where(Forecast.product_id == product_id)
    
    if from_date:
        query = query.where(Forecast.target_date >= from_date)
    if to_date:
        query = query.where(Forecast.target_date <= to_date)
    
    query = query.order_by(Forecast.target_date)
    
    result = await session.execute(query)
    forecasts = result.scalars().all()
    
    return [
        {
            "id": str(f.id),
            "target_date": f.target_date.isoformat(),
            "predicted_units": float(f.predicted_units),
            "model_run_id": str(f.model_run_id),
            "created_at": f.created_at.isoformat() if f.created_at else None
        }
        for f in forecasts
    ]
