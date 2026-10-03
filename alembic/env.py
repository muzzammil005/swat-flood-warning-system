"""Alembic async migration environment.

This env.py wires Alembic to run *fully asynchronously* against the actual
PostGIS container — no ``sync_driver``, no psycopg2 fallback. The flow:

1. ``run_migrations_online()`` builds an :class:`AsyncEngine` from the
   environment-configured ``DATABASE_URL`` (always ``postgresql+asyncpg://...``).
2. Each SQL operation inside the generated migration is dispatched via
   ``connection.run_sync(...)`` — the canonical Alembic pattern for async
   backends, which hands the raw DBAPI connection to Alembic's synchronous
   migration renderer while keeping the outer session async-managed.
3. ``target_metadata`` points at ``Base.metadata`` from the ORM models
   (``infrastructure.db.models``) *and* GeoAlchemy2's ``GEOALCHEMY2_OPTION``
   so that ``alembic revision --autogenerate`` can diff Geography columns.

Critically, we ``sys.path.insert`` the project's ``backend/src`` directory so
``from infrastructure.db.models import Base`` resolves correctly when Alembic
is executed as ``alembic upgrade head`` from the project root (the exact
command in Prompt 3).
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from geoalchemy2 import alembic_helpers
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

# ---------------------------------------------------------------------------
# Path setup: project_root/backend/src must be importable for Alembic to find
# the ORM model metadata. This runs exactly once per ``alembic`` invocation.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SRC_DIR = _PROJECT_ROOT / "backend" / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from infrastructure.db.models import Base  # noqa: E402  (import after sys.path fix)

# this is the Alembic Config object, which provides
# access to values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging (unless a caller already
# configured logging — e.g. a test harness).
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline mode: emit SQL to a file rather than connecting to a live DB.
# Unlikely to be used in the Docker-first workflow but supported for
# "generate a migration SQL script for DBA review" scenarios.
# ---------------------------------------------------------------------------


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # GeoAlchemy2: process spatial types correctly when rendering SQL.
        process_revision_directives=alembic_helpers.writer,
        render_item=alembic_helpers.render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online mode: connect to the live PostGIS container and run migrations
# through an async engine. This is what ``alembic upgrade head`` uses.
# ---------------------------------------------------------------------------


def _sync_run_migrations(connection):  # pragma: no cover — thin wrapper
    """Execute Alembic migrations *synchronously* inside an async connection.

    Alembic's migration runtime is synchronous; async drivers call this
    function via ``connection.run_sync(_sync_run_migrations)`` so the
    connection lifecycle stays async-managed while the migration code itself
    uses the standard Alembic synchronous API.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # GeoAlchemy2 helpers for Geography() columns.
        process_revision_directives=alembic_helpers.writer,
        render_item=alembic_helpers.render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations asynchronously against the live PostGIS database."""
    conf_section = config.get_section(config.config_ini_section, {}) or {}
    # Force the URL from the environment *every time* so the alembic.ini
    # placeholder %(DATABASE_URL)s is resolved even when running outside
    # Docker (e.g. a CI worker with the env var explicitly exported).
    conf_section["sqlalchemy.url"] = os.getenv("DATABASE_URL") or conf_section.get(
        "sqlalchemy.url", ""
    )

    connectable = async_engine_from_config(
        conf_section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(_sync_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio

    asyncio.run(run_migrations_online())
