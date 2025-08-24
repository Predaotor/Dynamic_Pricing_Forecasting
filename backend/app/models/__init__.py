# Ensure all model classes are imported and registered on Base.metadata
from .org import Organization  # noqa: F401
from .product import Product  # noqa: F401
from .sales import RawSales, SalesDaily, Cost  # noqa: F401
from .ml import ModelRun, Forecast, ElasticityEstimate, PriceRecommendation  # noqa: F401

