

"""Application configuration management using pydantic-settings."""

from typing import Any, List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """FarmShield AI Backend application settings loaded from environment or .env file."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "backend/.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application details
    APP_NAME: str = "FarmShield AI Backend"
    APP_ENV: str = "development"
    DEBUG: bool = True
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Database connection (psycopg3 PostgreSQL + PostGIS)
    DATABASE_URL: str = "postgresql+psycopg://farmshield:farmshield_password@localhost:5432/farmshield_db"

    # Database Pool Settings
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_PRE_PING: bool = True
    DB_CONNECT_TIMEOUT: int = 3

    # Security & Authentication
    JWT_SECRET_KEY: str = (
        "supersecret-jwt-placeholder-key-please-change-in-production-at-least-32-bytes"
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "farmshield-ai"
    JWT_AUDIENCE: str = "farmshield-app"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours (1440 minutes)

    # CORS configuration
    BACKEND_CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "https://farmfield-ai.vercel.app",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="after")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse CORS origins from a comma-separated string, JSON array, or list."""
        if isinstance(v, str):
            v_trimmed = v.strip()
            if v_trimmed.startswith("[") and v_trimmed.endswith("]"):
                import json
                try:
                    parsed = json.loads(v_trimmed)
                    if isinstance(parsed, list):
                        return [str(item) for item in parsed]
                except Exception:
                    pass
            return [i.strip() for i in v_trimmed.split(",") if i.strip()]
        return [str(item) for item in v]

    @property
    def is_production(self) -> bool:
        """Check if environment is set to production."""
        return self.APP_ENV.lower() == "production"

    def __repr__(self) -> str:
        """Safe representation hiding secrets to avoid accidental logging."""
        return (
            f"Settings(APP_NAME='{self.APP_NAME}', APP_ENV='{self.APP_ENV}', "
            f"DEBUG={self.DEBUG}, VERSION='{self.VERSION}', "
            f"DATABASE_URL='[REDACTED]', JWT_SECRET_KEY='[REDACTED]')"
        )


settings = Settings()
