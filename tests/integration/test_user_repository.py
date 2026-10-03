"""Integration tests for UserRepositoryImpl.

Covers: get_by_id (hit/miss), get_by_username (hit/miss), list_all (ordering),
add (round-trip of both roles), update (username, role, password_hash).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from domain.entities.user import User
from infrastructure.db.repositories import UserRepositoryImpl

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.ext.asyncio import AsyncSession


def _user(
    *,
    id: str,
    username: str = "muzzammil_admin",
    role: str = "admin",
    created_at: datetime,
) -> User:
    return User(
        id=id,
        username=username,
        role=role,  # type: ignore[arg-type]
        created_at=created_at,
    )


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_get_by_id_returns_user(
    session: AsyncSession, now: datetime
) -> None:
    repo = UserRepositoryImpl(session)
    await repo.add(_user(id="u-1", created_at=now))
    found = await repo.get_by_id("u-1")
    assert found is not None
    assert found.username == "muzzammil_admin"
    assert found.role == "admin"


@pytest.mark.integration
async def test_get_by_id_returns_none_for_unknown(session: AsyncSession) -> None:
    repo = UserRepositoryImpl(session)
    assert await repo.get_by_id("no-such-user") is None


# ---------------------------------------------------------------------------
# get_by_username
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_get_by_username_returns_user(
    session: AsyncSession, now: datetime
) -> None:
    repo = UserRepositoryImpl(session)
    await repo.add(_user(id="u-un", username="john_responder", created_at=now))
    found = await repo.get_by_username("john_responder")
    assert found is not None
    assert found.id == "u-un"


async def test_get_by_username_returns_none_for_unknown(
    session: AsyncSession,
) -> None:
    repo = UserRepositoryImpl(session)
    assert await repo.get_by_username("ghost") is None


async def test_get_by_username_case_sensitive_username(
    session: AsyncSession, now: datetime
) -> None:
    repo = UserRepositoryImpl(session)
    await repo.add(_user(id="u-case", username="AdminUser", created_at=now))
    # PostgreSQL collation is case‑sensitive unless specified otherwise.
    assert await repo.get_by_username("adminuser") is None
    assert await repo.get_by_username("AdminUser") is not None


# ---------------------------------------------------------------------------
# list_all
# ---------------------------------------------------------------------------


async def test_list_all_returns_asc_order_by_username(
    session: AsyncSession, now: datetime
) -> None:
    repo = UserRepositoryImpl(session)
    await repo.add(_user(id="u-z", username="zebra", created_at=now))
    await repo.add(_user(id="u-a", username="alpha", created_at=now))
    users = await repo.list_all()
    names = [u.username for u in users]
    assert names == sorted(names)


async def test_list_all_empty_when_no_users(session: AsyncSession) -> None:
    repo = UserRepositoryImpl(session)
    assert await repo.list_all() == []


# ---------------------------------------------------------------------------
# add — both roles round-trip
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("role", ["admin", "responder"])
async def test_both_roles_roundtrip(
    session: AsyncSession, now: datetime, role: str
) -> None:
    repo = UserRepositoryImpl(session)
    user = _user(id="u-role", username=f"user_{role}", role=role, created_at=now)
    saved = await repo.add(user)
    assert saved.role == role


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


async def test_update_changes_username(
    session: AsyncSession, now: datetime
) -> None:
    repo = UserRepositoryImpl(session)
    user = await repo.add(_user(id="u-name", created_at=now))
    renamed = User(
        id=user.id,
        username="new_name",
        role=user.role,
        created_at=user.created_at,
    )
    updated = await repo.update(renamed)
    assert updated.username == "new_name"
    assert await repo.get_by_username("new_name") is not None


async def test_update_changes_role(
    session: AsyncSession, now: datetime
) -> None:
    repo = UserRepositoryImpl(session)
    user = await repo.add(_user(id="u-rolechg", role="admin", created_at=now))
    promoted = User(
        id=user.id,
        username=user.username,
        role="responder",  # type: ignore[arg-type]
        created_at=user.created_at,
    )
    updated = await repo.update(promoted)
    assert updated.role == "responder"


async def test_update_preserves_password_hash_when_orm_stores_it(
    session: AsyncSession, now: datetime
) -> None:
    """password_hash is not part of the domain entity; it lives in the ORM
    column only. Ensure it's carried through when we load→mutate→save.
    This test must use the ORM directly to verify.
    """
    from infrastructure.db.models import UserModel

    repo = UserRepositoryImpl(session)
    # Insert a user with a password hash via raw ORM.
    user_orm = UserModel(
        id="u-pass",
        username="user_with_hash",
        role="admin",
        created_at=now,
        password_hash="argon2$...",
    )
    session.add(user_orm)
    await session.flush()
    # Load via repository.
    domain_user = await repo.get_by_id("u-pass")
    assert domain_user is not None
    # Update only username.
    updated_domain = User(
        id=domain_user.id,
        username="changed_name",
        role=domain_user.role,
        created_at=domain_user.created_at,
    )
    await repo.update(updated_domain)
    # Refetch via ORM.
    stmt = UserModel.__table__.select().where(UserModel.id == "u-pass")
    result = await session.execute(stmt)
    row = result.fetchone()
    assert row is not None
    # Use row._mapping for column name access
    assert row._mapping["password_hash"] == "argon2$..."
