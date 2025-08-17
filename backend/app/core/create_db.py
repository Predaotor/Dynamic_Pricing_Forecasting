from app.core.db import Base, engine
from app.models.product import Product  
from app.models.sales import RawSales, SalesDaily, Cost   
from app.models.org import Organization  
from app.models.ml import ModelRun, Forecast, ElasticityEstimate, PriceRecommendation  

# Create tables in the database 
Base.metadata.create_all(bind=engine)

