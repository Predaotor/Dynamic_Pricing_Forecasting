from multiprocessing import process
from fastapi import APIRouter, Depends, Body, BackgroundTasks
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.db import get_db, DATABASE_URL
from app.models.sales import RawSales
from app.etl.etl import run_etl
import asyncio

router = APIRouter()

@router.post("/sales/bulk")
def upload_raw_sales(rows: list[dict] = Body(...), source: str = "api", db: Session = Depends(get_db)):
    count = 0
    for payload in rows:
        db.add(RawSales(source=source, raw_json=payload, status="pending"))
        count += 1
    db.commit()
    return {"inserted": count}

@router.post("/run_etl")
def run_etl_endpoint(background_tasks: BackgroundTasks):
    async def _runner():
    # Coerce sync URL to asyncpg
      url = DATABASE_URL.set(drivername="postgresql+asyncpg")
      engine = create_async_engine(url, future=True, echo=False)
      AsyncLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

      async def _runner():
        async with AsyncLocal() as session:
            await run_etl(session)
        await engine.dispose()

    background_tasks.add_task(lambda: asyncio.run(_runner()))
    return {"status": "ETL started in background"}

@router.post("etl/status")
# query the RawSales.status counts to see progress:
async def etl_status(session: AsyncSession=Depends(get_db)):
    result=await session.execute( 
        select(
            func.count(RawSales.raw_id).filter(RawSales.status=="pending"),
            func.count(RawSales.raw_id).filter(RawSales.status=="processed"),
            func.count(RawSales.raw_id).filter(RawSales.status=="failed")
        )
        )
    pending, processed, failed=result.one()
    return {"pending":pending, "processed":processed, "failed":failed}
