import asyncio 
import logging  
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine 
from sqlalchemy.orm import sessionmaker  
from app.core.db import DATABASE_URL 
from app.etl.etl import run_etl 

logging.basicConfig(level=logging.INFO) 
logger = logging.getLogger(__name__)  

async def main():
    url = DATABASE_URL.set(drivername="postgresql+asyncpg")
    engine = create_async_engine(url, future=True, echo=False)
    AsyncLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncLocal() as session:
        await run_etl(session)
        
    await engine.dispose() 
    logger.info("Worker finished ETL job.")
    
if __name__ == "__main__":
    asyncio.run(main())
        