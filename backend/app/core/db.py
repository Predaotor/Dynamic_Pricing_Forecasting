# backend app database 
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

import os 
from dotenv import load_dotenv

load_dotenv() # Load environment variables 

# Get DATABASE_URL from environment
# For local development, use DATABASE_PUBLIC_URL (external Railway URL)
# For Railway deployment, use DATABASE_URL (internal Railway URL)
DATABASE_URL = os.getenv("DATABASE_PUBLIC_URL") or os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_PUBLIC_URL or DATABASE_URL environment variable is required")

# For Railway deployment, use the internal URL
# For local development, use the external URL
# Railway provides both internal and external URLs
# Use external URL for local development to avoid connection issues
if "railway.internal" in DATABASE_URL:
    # Replace internal hostname with external hostname for local development
    DATABASE_URL = DATABASE_URL.replace("railway.internal", "railway.app")

# Create engine with DATABASE_URL
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Create all tables (automatically)
def init_db() -> None:
    """
    Initializes the database by creating all tables.
    """
    Base.metadata.create_all(bind=engine)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()