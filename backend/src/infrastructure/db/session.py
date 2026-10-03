"""Async SQLAlchemy engine + session factory.

The DB session configuration lives here rather than in a FastAPI dependency so
that non-HTTP code paths (background risk-cycle tasks, one-off migration
scripts, pytest integration tests) can use the *exact* same session setup as
the HTTP handlers in Stage 4.

Async driver: ``asyncpg`` (pure-Python, well-maintained). The engine is
configured with ``pool_pre_ping=True`` which defends against stale pooled
connections — a classic failure mode when the Docker PostGIS container is
restarted while the backend keeps running.

The ``get_session()`` async context manager is the canonical way to acquire a
session anywhere in the app. Stage 4 will wrap it in a FastAPI Depends() but
the implementation itself is framework-free.
"""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


class DBSettings:
    """Environment-variable-backed DB config.

    We intentionally don't use pydantic-settings here because the Alembic
    ``env.py`` runner executes *before* the application package import graph
    is fully resolved (and pydantic-settings is not a required dep for a
    migration runner, which is a standalone script).
    """

    DATABASE_URL: str

    def __init__(self) -> None:
        url = os.getenv("DATABASE_URL")
        if not url:
            raise RuntimeError(
                "DATABASE_URL environment variable is not set. "
                "Running locally? The backend docker-compose service sets this "
                "automatically; running outside compose, export it to the same "
                "value compose uses (postgresql+asyncpg://...)."
            )
        self.DATABASE_URL = url


_settings = DBSettings()

# Reuse a single engine per event loop. asyncpg connections are bound to the
# loop that created them, so a process-wide singleton is unsafe when tests or
# reloads create a fresh asyncio loop.
_engine: AsyncEngine | None = None
_engine_by_loop: dict[int, AsyncEngine] = {}


def get_engine() -> AsyncEngine:
    """Return an engine bound to the current running event loop, if any."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        global _engine
        if _engine is None:
            _engine = create_async_engine(
                _settings.DATABASE_URL,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
                echo=False,
                connect_args={
                    "server_settings": {
                        "application_name": "swat-flood-backend",
                    },
                },
            )
        return _engine

    existing = _engine_by_loop.get(id(loop))
    if existing is not None:
        return existing

    engine = create_async_engine(
        _settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=False,
        connect_args={
            "server_settings": {
                "application_name": "swat-flood-backend",
            },
        },
    )
    _engine_by_loop[id(loop)] = engine
    return engine


_AsyncSessionLocal: async_sessionmaker[AsyncSession] | None = None
_AsyncSessionLocal_by_loop: dict[int, async_sessionmaker[AsyncSession]] = {}


def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        global _AsyncSessionLocal
        if _AsyncSessionLocal is None:
            _AsyncSessionLocal = async_sessionmaker(
                bind=get_engine(),
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
            )
        return _AsyncSessionLocal

    factory = _AsyncSessionLocal_by_loop.get(id(loop))
    if factory is None:
        factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        _AsyncSessionLocal_by_loop[id(loop)] = factory
    return factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager yielding a fresh transaction-scoped session.

    Commits on clean exit, rolls back on any exception, closes the session
    in either case. Stage 4 HTTP routers will wrap this in a FastAPI
    ``Depends`` but application-layer use cases are encouraged to call it
    directly via ``async with get_session() as session: ...``.
    """
    factory = _get_session_factory()
    async with factory() as session, session.begin():
        yield session


__all__ = ["AsyncSession", "DBSettings", "get_engine", "get_session"]
