# backend app database 
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.engine import URL
import os 
from dotenv import load_dotenv

load_dotenv() # Load environment variables 

# Get DATABASE_URL from environment
# For local development, use DATABASE_PUBLIC_URL (external Railway URL)
# For Railway deployment, use DATABASE_URL (internal Railway URL)
DATABASE_URL_1 = os.getenv("DATABASE_PUBLIC_URL") or os.getenv("DATABASE_URL")

DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

DATABASE_URL =URL.create(
    drivername="postgresql+psycopg2",
    username=DB_USERNAME,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME
)   # only the password field


if not DATABASE_URL:
    raise ValueError("DATABASE_PUBLIC_URL or DATABASE_URL environment variable is required")

# For Railway deployment, use the internal URL
# For local development, use the external URL
# Railway provides both internal and external URLs
# Use external URL for local development to avoid connection issues
"""if "railway.internal" in DATABASE_URL:
    # Replace internal hostname with external hostname for local development
    DATABASE_URL = DATABASE_URL.replace("railway.internal", "railway.app")
"""
# Create engine with DATABASE_URL
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
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