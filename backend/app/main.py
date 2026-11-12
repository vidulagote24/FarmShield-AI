"""FarmShield AI Backend - Main FastAPI Application Entrypoint."""

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict
from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints.health import get_health
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import setup_exception_handlers
from app.core.logging import logger
from app.schemas import HealthResponse, ServiceInfoResponse


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan event handler for startup and shutdown procedures."""
    logger.info(
        f"Starting {settings.APP_NAME} v{settings.VERSION} [{settings.APP_ENV}]"
    )
    logger.info(f"API documentation available at /docs and /redoc")
    logger.info(f"Configured CORS origins: {settings.BACKEND_CORS_ORIGINS}")
    yield
    logger.info(f"Shutting down {settings.APP_NAME}")


# Initialize FastAPI application with OpenAPI specifications
app = FastAPI(
    title="FarmShield AI Backend",
    description="Precision Agriculture and Farm Management Backend Platform.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Configure CORS Middleware from environment settings
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Setup custom exception handling
setup_exception_handlers(app)

# Include Versioned API v1 Router (/api/v1)
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get(
    "/",
    response_model=ServiceInfoResponse,
    summary="Root Service Status",
    description="Returns primary service metadata and links to API documentation.",
    tags=["Root"],
    status_code=status.HTTP_200_OK,
)
def root_service_info() -> Dict[str, Any]:
    """Root endpoint returning basic service status."""
    return {
        "app_name": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "operational",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "api_prefix": settings.API_V1_STR,
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Root Health Check",
    description="Returns service health status, environment, and database connectivity.",
    tags=["Health"],
    status_code=status.HTTP_200_OK,
)
def root_health(response: Response) -> Dict[str, Any]:
    """Top-level health check endpoint for orchestrators and container probes."""
    return get_health(response=response)
