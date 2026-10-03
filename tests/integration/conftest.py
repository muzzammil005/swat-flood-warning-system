"""Integration-test fixtures for repository tests against a live PostGIS container.

Design notes:

1. **Rollback strategy.** Each test gets its own engine and session to avoid
   event loop issues. Tests are isolated via savepoints (nested transactions).

2. **Always start with a zone.** 11 of the 12 repositories have an FK to
   ``zones`` (only ``users``, ``api_keys``, and ``audit_log_entries`` don't).
   The ``zone_a`` / ``zone_b`` fixtures create two well-known zones so tests
   don't need to hand-roll Coordinates + Zone in every single case.

3. **Transaction note.** Postgres can read back geography/geometry values written
   earlier in the same transaction without a COMMIT; SAVEPOINT rollback works
   fine for GeoAlchemy2 WKB serialization round-trip testing.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from domain.entities.zone import Zone
from domain.value_objects.coordinates import Coordinates
from infrastructure.db.repositories import ZoneRepositoryImpl

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@pytest.fixture()
async def session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a live DB session; each test gets its own engine and isolated savepoint."""
    import os
    url = os.getenv("DATABASE_URL", "postgresql+asyncpg://swat:swat_dev_password@postgres:5432/swat_flood")
    
    # Create a fresh engine for each test to avoid event loop issues
    engine = create_async_engine(
        url,
        pool_pre_ping=True,
        pool_size=5,  # Smaller pool for single-test use
        max_overflow=10,
        echo=False,
        connect_args={
            "server_settings": {
                "application_name": "swat-flood-tests",
            },
        },
    )
    
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    
    async with session_factory() as s:
        # Start outer transaction
        await s.begin()
        # Create a savepoint for test isolation
        await s.begin_nested()
        try:
            yield s
        finally:
            # Rollback the savepoint, undoing all test changes
            await s.rollback()
            # Rollback the outer transaction
            await s.rollback()
    
    await engine.dispose()


@pytest.fixture()
async def zone_a(session: AsyncSession) -> Zone:
    """Stable first zone — upstream headwater."""
    z = Zone(
        id="zone-kalam",
        name="Kalam Bazaar",
        coordinates=Coordinates(latitude=35.479, longitude=72.596),
        upstream_zone_id=None,
    )
    repo = ZoneRepositoryImpl(session)
    return await repo.add(z)


@pytest.fixture()
async def zone_b(session: AsyncSession, zone_a: Zone) -> Zone:
    """Stable second zone — downstream of zone_a."""
    z = Zone(
        id="zone-mingora",
        name="Mingora City",
        coordinates=Coordinates(latitude=34.774, longitude=72.361),
        upstream_zone_id=zone_a.id,
    )
    repo = ZoneRepositoryImpl(session)
    return await repo.add(z)


@pytest.fixture()
def now() -> datetime:
    """Freeze a single ``datetime.now(UTC)`` per test call for reproducibility."""
    return datetime.now(UTC)
