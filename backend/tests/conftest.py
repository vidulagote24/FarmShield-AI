"""Root test fixtures for backend/tests, reusing app/tests/conftest.py."""

from app.tests.conftest import client, db_session

__all__ = ["db_session", "client"]
