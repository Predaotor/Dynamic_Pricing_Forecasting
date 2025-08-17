from app.core import Base
from app.core import engine

# Create tables in the database 
Base.metadata.create_all(bind=engine)

