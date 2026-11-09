"""Alembic environment configuration for database migrations."""

import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Ensure app package is importable from backend directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.db.base import Base
# Import models to ensure they are registered with Base.metadata
import app.models  # noqa: F401

config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for 'autogenerate' support
target_metadata = Base.metadata

# Override sqlalchemy.url with the settings.DATABASE_URL from environment / .env
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)


def include_object(object, name, type_, reflected, compare_to):
    """Filter out PostGIS system tables and non-public tables/schemas."""
    if getattr(object, "schema", None) is not None and object.schema != "public":
        return False
    if type_ == "table":
        if name in (
            "spatial_ref_sys",
            "geography_columns",
            "geometry_columns",
            "raster_columns",
            "raster_overviews",
            "alembic_version",
            "layer",
            "topology",
        ):
            return False
        # Do not drop tables that belong to PostGIS / tiger / topology
        if reflected and name not in target_metadata.tables:
            return False
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    from app.db.session import engine
    import sqlalchemy as sa

    with engine.connect() as connection:
        # Enforce search_path to public so PostGIS tiger/topology schemas are not reflected
        connection.execute(sa.text("SET search_path TO public;"))
        connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()

        connection.commit()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
