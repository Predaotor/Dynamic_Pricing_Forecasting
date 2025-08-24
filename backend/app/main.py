from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from app.core.db import init_db
import app.models  # ensure models are registered
from app.routers.health import router as health_router
from app.routers.products import router as products_router
from app.routers.sales import router as sales_router
from app.routers.ml import router as ml_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    yield
    # Shutdown

app = FastAPI(title="Dynamic Pricing & Forecasting API", version="1.0.0", lifespan=lifespan)

origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health_router, prefix="")
app.include_router(products_router, prefix="")
app.include_router(sales_router, prefix="")
app.include_router(ml_router, prefix="")

