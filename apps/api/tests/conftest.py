"""Test configuration and shared fixtures."""
from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from forgeops.db import Base, get_db

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(
        bind=test_engine, expire_on_commit=False, autoflush=False
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    # Import lazily so the module-level engine is not created yet
    import forgeops.db as db_module

    # Point the singleton at our test engine
    db_module._engine = db_session.bind  # type: ignore[assignment]

    from forgeops.app import create_app

    app = create_app()

    # FastAPI dependency override must be an async generator function
    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()
    db_module._engine = None


@pytest.fixture
def sample_mission() -> dict[str, Any]:
    return {
        "title": "Investigate revenue pipeline failure",
        "description": (
            "The customer revenue pipeline failed overnight. "
            "Find the root cause, fix it and create a pull request."
        ),
        "max_steps": 20,
        "max_cost_usd": 1.0,
    }
