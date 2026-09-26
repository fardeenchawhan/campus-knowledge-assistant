from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from main import app
from src.core.config import settings
from src.core.database import get_db
from src.core.rate_limit import RateLimiter


TEST_DATABASE_URL = (
    settings.DATABASE_URL.rsplit("/", 1)[0]
    + "/campus_knowledge_test"
)


@pytest_asyncio.fixture
async def test_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )

    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def test_session_factory(test_engine):
    return async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest_asyncio.fixture
async def clean_database(test_engine):
    async with test_engine.begin() as connection:
        await connection.exec_driver_sql(
            """
            TRUNCATE TABLE
                users,
                chunks,
                document_versions,
                documents
            RESTART IDENTITY CASCADE
            """
        )


@pytest_asyncio.fixture
async def db(
    clean_database,
    test_session_factory,
) -> AsyncGenerator[AsyncSession, None]:

    async with test_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(
    clean_database,
    test_session_factory,
    monkeypatch,
):
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async def disable_rate_limit(
        self,
        key: str,
    ) -> None:
        return None

    monkeypatch.setattr(
        RateLimiter,
        "check",
        disable_rate_limit,
    )

    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)