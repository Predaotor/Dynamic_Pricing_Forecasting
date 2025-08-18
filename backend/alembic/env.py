from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys

# Add app directory to sys.path
# Add backend/ to PYTHONPATH so "app" becomes importable
sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))

from app.core.db import Base, DATABASE_URL
from app.models.ml import ModelRun, Forecast, ElasticityEstimate, PriceRecommendation
from app.models.product import Product
from app.models.sales import RawSales, SalesDaily, Cost
from app.models.org import Organization

# Alembic Config object
config = context.config

# Override URL from db.py
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Interpret logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
