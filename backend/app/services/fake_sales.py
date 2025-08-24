import asyncio 
from datetime import  datetime, timezone, timedelta
import random
import json 
from sqlalchemy import future
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession 
from uuid import uuid4 
from sqlalchemy.orm import  sessionmaker 
from app.models.sales import RawSales 
from app.core.db import DATABASE_URL 

# Configure async engine and session 
engine=create_async_engine(DATABASE_URL, echo=False, future=True)
async_session=sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Synthetic data settings-- 
NUM_RECORDS=1_000_000 # total records to generate 
BATCH_SIZE=10_000 # insert per commit 
NUM_PRODUCTS=500 # number of unique products 

START_DATE=datetime(2024, 1, 1, tzinfo=timezone.utc)

def generate_fake_sales(product_ids):
        # Generate a single fake sales row JSON 
    product_id=random.choice(product_ids)
    sale_date=START_DATE+timedelta(days=random.randint(0, 600))
    units_sold=max(1, int(random.gauss(20, 5))) # normal distribution 
    price=round(random.uniform(5,100), 2)
    
    # Sometimes insert some outliers 
    if random.random()<0.01:
        units_sold*=random.randint(5,20)
        
    data= {
        "product_id":str(product_id),
        "date":sale_date.date().isoformat(),
        "units_sold":units_sold, 
        "price":price, 
        "revenue":round(units_sold*price, 2)
    }
    
    return data 

async def generate_sales():
    product_ids=[uuid4() for _ in range(NUM_PRODUCTS)]
    
    async with async_session() as session: 
        for batch_start in range(0, NUM_RECORDS, BATCH_SIZE):
            batch=[] 
            for _ in range(BATCH_SIZE):
                sale=generate_fake_sales(product_ids)
                batch.append(
                    RawSales(
                        raw_json=json.dumps(sale),
                        source="synthetic", 
                        status="pending",
                        error_message=None,
                    )
                )
            session.add_all(batch)
            await session.commit() 
            print(f"Inserted {batch_start+BATCH_SIZE}/{NUM_RECORDS} rows ...")

if __name__=="__main__":
    asyncio.run(generate_sales())