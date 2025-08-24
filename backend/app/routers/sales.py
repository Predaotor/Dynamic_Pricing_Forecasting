from fastapi import APIRouter, Depends, Body
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
def run_etl_endpoint():
    # Coerce sync URL to asyncpg
    url = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://").replace("+psycopg2", "+asyncpg")
    engine = create_async_engine(url, future=True, echo=False)
    AsyncLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async def _runner():
        async with AsyncLocal() as session:
            await run_etl(session)
        await engine.dispose()

    asyncio.run(_runner())
    return {"status": "ok"}
