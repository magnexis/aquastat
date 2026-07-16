from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, async_sessionmaker, create_async_engine

from app.core.config import settings


engine: AsyncEngine | None = None
SessionLocal: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global engine, SessionLocal
    if engine is None:
        engine = create_async_engine(settings.database_url, echo=False)
        SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    return engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if SessionLocal is None:
        get_engine()
    assert SessionLocal is not None
    return SessionLocal


async def get_session() -> AsyncIterator[AsyncSession]:
    factory = get_session_factory()
    async with factory() as session:
        yield session
