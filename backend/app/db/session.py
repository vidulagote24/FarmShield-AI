"""Database engine, session management, and connectivity diagnostics."""

from contextlib import contextmanager
from typing import Any, Dict, Generator
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from app.core.config import settings
from app.core.logging import logger

# Create SQLAlchemy 2.x engine using psycopg3
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=settings.DB_POOL_PRE_PING,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    connect_args={"connect_timeout": settings.DB_CONNECT_TIMEOUT},
    echo=False,
)

# Factory for creating new database sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager for standalone transactional database sessions."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.error(f"Database session rolled back due to error: {exc}")
        raise
    finally:
        session.close()


def check_db_connection() -> Dict[str, Any]:
    """Safely verify database and PostGIS connectivity without leaking credentials.

    Returns:
        dict: Diagnostics dictionary containing connection status and PostGIS info.
    """
    diagnostics: Dict[str, Any] = {
        "connected": False,
        "database": "postgresql",
        "postgis_installed": False,
        "postgis_version": None,
        "error": None,
    }

    try:
        with engine.connect() as connection:
            # 1. Test basic connectivity
            result = connection.execute(text("SELECT 1;"))
            if result.scalar() == 1:
                diagnostics["connected"] = True

            # 2. Test PostGIS extension
            try:
                postgis_result = connection.execute(
                    text("SELECT PostGIS_Full_Version();")
                )
                raw_version = postgis_result.scalar()
                diagnostics["postgis_installed"] = True
                diagnostics["postgis_version"] = (
                    str(raw_version).split()[0] if raw_version else "detected"
                )
            except SQLAlchemyError:
                # PostGIS extension not yet loaded or not present
                diagnostics["postgis_installed"] = False

    except SQLAlchemyError as err:
        logger.warning(f"Database health check failed: {err.__class__.__name__}")
        diagnostics["connected"] = False
        diagnostics["error"] = "Database connection unavailable"
    except Exception as err:
        logger.warning(f"Unexpected database check failure: {err.__class__.__name__}")
        diagnostics["connected"] = False
        diagnostics["error"] = "Service connection error"

    return diagnostics
