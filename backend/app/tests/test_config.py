"""Tests for application settings and configuration."""

from app.core.config import Settings, settings


def test_default_settings() -> None:
    """Verify default settings values."""
    assert settings.APP_NAME == "FarmShield AI Backend"
    assert settings.VERSION == "1.0.0"
    assert settings.API_V1_STR == "/api/v1"
    assert settings.JWT_ALGORITHM == "HS256"
    assert "postgresql" in settings.DATABASE_URL
    assert "psycopg" in settings.DATABASE_URL


def test_cors_origin_parsing() -> None:
    """Verify CORS origins parsing from comma-separated string."""
    test_settings = Settings(BACKEND_CORS_ORIGINS="http://localhost:3000,http://example.com")
    assert "http://localhost:3000" in test_settings.BACKEND_CORS_ORIGINS
    assert "http://example.com" in test_settings.BACKEND_CORS_ORIGINS


def test_secrets_redacted_in_repr() -> None:
    """Verify that sensitive values are masked in repr to prevent log leakage."""
    rep = repr(settings)
    assert "[REDACTED]" in rep
    assert settings.JWT_SECRET_KEY not in rep
