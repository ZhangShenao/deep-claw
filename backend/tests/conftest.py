"""Pytest fixtures: env must be set before importing the FastAPI app."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

# Defaults for integration tests (GitHub Actions services + local docker compose ports)
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/deep_claw")
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGODB_DB_NAME", "deep_claw")
os.environ.setdefault("OPENAI_API_KEY", "ci-test-placeholder")
os.environ.setdefault("OPENAI_BASE_URL", "http://127.0.0.1:9/v1")
os.environ.setdefault("OPENAI_MODEL", "glm-4-plus")
os.environ.setdefault("CORS_ORIGINS", "*")
os.environ.setdefault("EMAIL_CREDENTIAL_KEY", "test-email-credential-key")

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from app.config import get_settings

get_settings.cache_clear()

from app.main import app  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import async_session_factory  # noqa: E402
from app.db.session import engine  # noqa: E402


@pytest_asyncio.fixture(autouse=True)
async def reset_database() -> AsyncIterator[None]:
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(delete(table))
    yield


@pytest_asyncio.fixture
async def async_client() -> AsyncIterator[AsyncClient]:
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            yield client


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator:
    async with async_session_factory() as session:
        yield session
