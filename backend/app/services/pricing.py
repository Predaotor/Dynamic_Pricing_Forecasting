"""
Pricing Service - Recommend optimal prices using elasticity and demand curves.
Following Instructions.md 5.3: For each forecasted date, compute demand curve using elasticity.
Optimize price within [pmin, pmax] (defaults [0.5*P0, 1.5*P0]).
Write suggested_prices including expected units/revenue/profit.
"""

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.sales import SalesDaily, Cost
from app.models.ml import ModelRun, PriceRecommendation, Forecast, ElasticityEstimate
from app.models.product import Product
from datetime import date, timedelta
from typing import List, Optional, Tuple
from uuid import uuid4
import logging

logger = logging.getLogger(__name__)


def calculate_demand_curve(
    baseline_price: float,
    baseline_quantity: float,
    elasticity: float,
    price_range: Tuple[float, float],
    num_points: int = 100
) -> Tuple[List[float], List[float]]:
    """
    Calculate demand curve using elasticity: D(p) = D0 * (p/P0)^b
    
    Args:
        baseline_price: Current/reference price P0
        baseline_quantity: Current/reference quantity D0
        elasticity: Price elasticity b (typically negative)
        price_range: (min_price, max_price) tuple
        num_points: Number of price points to evaluate
        
    Returns:
        Tuple of (prices, quantities)
    """
    min_price, max_price = price_range
    prices = np.linspace(min_price, max_price, num_points)
    
    # Demand curve: D(p) = D0 * (p/P0)^b
    quantities = baseline_quantity * (prices / baseline_price) ** elasticity
    
    return prices.tolist(), quantities.tolist()


def optimize_price_objective(
    prices: List[float],
    quantities: List[float],
    objective: str,
    unit_cost: Optional[float] = None
) -> Tuple[float, float, float, float]:
    """
    Find optimal price for given objective (revenue or profit).
    
    Args:
        prices: List of price points
        quantities: List of corresponding quantities
        objective: 'revenue' or 'profit'
        unit_cost: Cost per unit (required for profit optimization)
        
    Returns:
        Tuple of (optimal_price, optimal_quantity, expected_revenue, expected_profit)
    """
    if objective == 'revenue':
        # Maximize R(p) = p * D(p)
        revenues = [p * q for p, q in zip(prices, quantities)]
        max_idx = np.argmax(revenues)
        
        optimal_price = prices[max_idx]
        optimal_quantity = quantities[max_idx]
        expected_revenue = revenues[max_idx]
        expected_profit = None  # Not calculated for revenue objective
        
    elif objective == 'profit':
        if unit_cost is None:
            raise ValueError("unit_cost required for profit optimization")
            
        # Maximize π(p) = (p-c) * D(p)
        profits = [(p - unit_cost) * q for p, q in zip(prices, quantities)]
        max_idx = np.argmax(profits)
        
        optimal_price = prices[max_idx]
        optimal_quantity = quantities[max_idx]
        expected_revenue = optimal_price * optimal_quantity
        expected_profit = profits[max_idx]
        
    else:
        raise ValueError("objective must be 'revenue' or 'profit'")
    
    return optimal_price, optimal_quantity, expected_revenue, expected_profit


async def recommend_prices(
    session: AsyncSession,
    product_id: str,
    objective: str = "revenue",
    pmin: Optional[float] = None,
    pmax: Optional[float] = None,
    target_dates: Optional[List[date]] = None,
    horizon: int = 30
) -> dict:
    """
    Recommend optimal prices for a product.
    
    Args:
        session: Async database session
        product_id: Product UUID
        objective: 'revenue' or 'profit'
        pmin: Minimum price (defaults to 0.5 * baseline_price)
        pmax: Maximum price (defaults to 1.5 * baseline_price)
        target_dates: Specific dates to recommend for (defaults to next horizon days)
        horizon: Number of days to forecast if target_dates not provided
        
    Returns:
        dict with price recommendations and model metadata
    """
    
    # Get product info
    product_result = await session.execute(
        select(Product).where(Product.id == product_id)
    )
    product = product_result.scalar_one_or_none()
    
    if not product:
        raise ValueError(f"Product {product_id} not found")
    
    # Get latest elasticity estimate
    elasticity_result = await session.execute(
        select(ElasticityEstimate)
        .where(ElasticityEstimate.product_id == product_id)
        .order_by(ElasticityEstimate.created_at.desc())
        .limit(1)
    )
    elasticity_estimate = elasticity_result.scalar_one_or_none()
    
    if not elasticity_estimate:
        raise ValueError(f"No elasticity estimate found for product {product_id}")
    
    elasticity = float(elasticity_estimate.elasticity)
    
    # Get latest sales data for baseline
    latest_sales_result = await session.execute(
        select(SalesDaily.price, SalesDaily.units_sold)
        .where(SalesDaily.product_id == product_id)
        .order_by(SalesDaily.date.desc())
        .limit(1)
    )
    latest_sales = latest_sales_result.fetchone()
    
    if not latest_sales:
        raise ValueError(f"No sales data found for product {product_id}")
    
    baseline_price = float(latest_sales.price)
    baseline_quantity = float(latest_sales.units_sold)
    
    # Set price bounds if not provided
    if pmin is None:
        pmin = baseline_price * 0.5
    if pmax is None:
        pmax = baseline_price * 1.5
    
    # Validate price bounds
    if pmin >= pmax:
        raise ValueError("pmin must be less than pmax")
    if pmin <= 0:
        raise ValueError("pmin must be positive")
    
    # Get unit cost if optimizing for profit
    unit_cost = None
    if objective == "profit":
        cost_result = await session.execute(
            select(Cost.unit_cost)
            .where(Cost.product_id == product_id)
            .order_by(Cost.date.desc())
            .limit(1)
        )
        cost_row = cost_result.fetchone()
        if cost_row:
            unit_cost = float(cost_row.unit_cost)
        else:
            logger.warning(f"No cost data found for product {product_id}, using 0")
            unit_cost = 0.0
    
    # Determine target dates
    if target_dates is None:
        # Use next horizon days
        start_date = date.today() + timedelta(days=1)
        target_dates = [start_date + timedelta(days=i) for i in range(horizon)]
    
    # Get forecasts for target dates
    forecasts_result = await session.execute(
        select(Forecast.target_date, Forecast.predicted_units)
        .where(
            Forecast.product_id == product_id,
            Forecast.target_date.in_(target_dates)
        )
    )
    forecasts = {f.target_date: f.predicted_units for f in forecasts_result.scalars().all()}
    
    # Store model run
    model_run = ModelRun(
        id=uuid4(),
        model_name="price_optimization",
        model_version="1.0",
        params={
            "objective": objective,
            "pmin": pmin,
            "pmax": pmax,
            "baseline_price": baseline_price,
            "baseline_quantity": baseline_quantity,
            "elasticity": elasticity,
            "elasticity_r2": float(elasticity_estimate.r2),
            "unit_cost": unit_cost,
            "target_dates": [d.isoformat() for d in target_dates],
            "horizon": horizon
        }
    )
    session.add(model_run)
    await session.flush()
    
    # Generate price recommendations for each target date
    recommendations = []
    
    for target_date in target_dates:
        # Use forecasted quantity or baseline if no forecast
        forecasted_quantity = forecasts.get(target_date, baseline_quantity)
        
        # Calculate demand curve
        prices, quantities = calculate_demand_curve(
            baseline_price=baseline_price,
            baseline_quantity=forecasted_quantity,
            elasticity=elasticity,
            price_range=(pmin, pmax)
        )
        
        # Find optimal price
        optimal_price, optimal_quantity, expected_revenue, expected_profit = optimize_price_objective(
            prices=prices,
            quantities=quantities,
            objective=objective,
            unit_cost=unit_cost
        )
        
        # Create recommendation record
        recommendation = PriceRecommendation(
            product_id=product_id,
            model_run_id=model_run.id,
            target_date=target_date,
            objective=objective,
            suggested_price=optimal_price,
            expected_units=optimal_quantity,
            expected_revenue=expected_revenue,
            expected_profit=expected_profit if expected_profit is not None else 0.0
        )
        recommendations.append(recommendation)
        
        # Store in database
        session.add(recommendation)
    
    await session.commit()
    
    return {
        "model_run_id": str(model_run.id),
        "objective": objective,
        "elasticity": elasticity,
        "baseline_price": baseline_price,
        "price_range": {"min": pmin, "max": pmax},
        "recommendations": [
            {
                "target_date": r.target_date.isoformat(),
                "suggested_price": float(r.suggested_price),
                "expected_units": float(r.expected_units),
                "expected_revenue": float(r.expected_revenue),
                "expected_profit": float(r.expected_profit)
            }
            for r in recommendations
        ]
    }


async def get_price_recommendations(
    session: AsyncSession,
    product_id: str,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    objective: Optional[str] = None
) -> List[dict]:
    """
    Retrieve price recommendations for a product within a date range.
    
    Args:
        session: Async database session
        product_id: Product UUID
        from_date: Start date (inclusive)
        to_date: End date (inclusive)
        objective: Filter by objective ('revenue' or 'profit')
        
    Returns:
        List of price recommendation records
    """
    query = select(PriceRecommendation).where(PriceRecommendation.product_id == product_id)
    
    if from_date:
        query = query.where(PriceRecommendation.target_date >= from_date)
    if to_date:
        query = query.where(PriceRecommendation.target_date <= to_date)
    if objective:
        query = query.where(PriceRecommendation.objective == objective)
    
    query = query.order_by(PriceRecommendation.target_date)
    
    result = await session.execute(query)
    recommendations = result.scalars().all()
    
    return [
        {
            "id": str(r.id),
            "target_date": r.target_date.isoformat(),
            "objective": r.objective,
            "suggested_price": float(r.suggested_price),
            "expected_units": float(r.expected_units),
            "expected_revenue": float(r.expected_revenue),
            "expected_profit": float(r.expected_profit),
            "model_run_id": str(r.model_run_id),
            "created_at": r.created_at.isoformat() if r.created_at else None
        }
        for r in recommendations
    ]
