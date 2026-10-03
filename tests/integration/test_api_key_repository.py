"""Integration tests for APIKeyRepositoryImpl.

Covers: get_by_id (hit/miss), get_by_hash (hit/miss), list_active (filtering),
add (round-trip), update (key_hash, owner_name, is_active toggle).
"""

from __future__ import annotations
import pytest

from typing import TYPE_CHECKING

from domain.entities.api_key import APIKey
from infrastructure.db.repositories import APIKeyRepositoryImpl

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def _key(
    *,
    id: str,
    key_hash: str | None = None,
    owner_name: str = "IoT logger",
    is_active: bool = True,
) -> APIKey:
    # Generate unique key hash based on id to avoid unique constraint violations
    if key_hash is None:
        key_hash = f"sha256${id}-unique-hash"
    return APIKey(
        id=id,
        key_hash=key_hash,
        owner_name=owner_name,
        is_active=is_active,
    )


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_get_by_id_returns_key(session: AsyncSession) -> None:
    repo = APIKeyRepositoryImpl(session)
    await repo.add(_key(id="ak-1"))
    found = await repo.get_by_id("ak-1")
    assert found is not None
    assert found.key_hash.startswith("sha256$")


@pytest.mark.integration
async def test_get_by_id_returns_none_for_unknown(session: AsyncSession) -> None:
    repo = APIKeyRepositoryImpl(session)
    assert await repo.get_by_id("no-such-key") is None


# ---------------------------------------------------------------------------
# get_by_hash
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_get_by_hash_returns_key(session: AsyncSession) -> None:
    repo = APIKeyRepositoryImpl(session)
    await repo.add(_key(id="ak-hash", key_hash="sha256$xyz789"))
    found = await repo.get_by_hash("sha256$xyz789")
    assert found is not None
    assert found.id == "ak-hash"


@pytest.mark.integration
async def test_get_by_hash_returns_none_for_unknown(session: AsyncSession) -> None:
    repo = APIKeyRepositoryImpl(session)
    assert await repo.get_by_hash("sha256$ghost") is None


# ---------------------------------------------------------------------------
# list_active
# ---------------------------------------------------------------------------


async def test_list_active_filters_by_is_active(
    session: AsyncSession,
) -> None:
    repo = APIKeyRepositoryImpl(session)
    await repo.add(_key(id="ak-act", is_active=True))
    await repo.add(_key(id="ak-rev", is_active=False))
    active = await repo.list_active()
    assert len(active) == 1
    assert active[0].id == "ak-act"


async def test_list_active_orders_asc_by_owner_name(
    session: AsyncSession,
) -> None:
    repo = APIKeyRepositoryImpl(session)
    await repo.add(_key(id="ak-z", owner_name="Zebra sensor", is_active=True))
    await repo.add(_key(id="ak-a", owner_name="Alpha scraper", is_active=True))
    active = await repo.list_active()
    names = [k.owner_name for k in active]
    assert names == sorted(names)


@pytest.mark.integration
async def test_list_active_empty_when_no_active_keys(session: AsyncSession) -> None:
    repo = APIKeyRepositoryImpl(session)
    await repo.add(_key(id="ak-inactive", is_active=False))
    assert await repo.list_active() == []


# ---------------------------------------------------------------------------
# add — round-trip
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_add_roundtrips_all_fields(session: AsyncSession) -> None:
    repo = APIKeyRepositoryImpl(session)
    key = APIKey(
        id="ak-full",
        key_hash="argon2$deadbeef",
        owner_name="Batch processor",
        is_active=False,
    )
    saved = await repo.add(key)
    assert saved.key_hash == "argon2$deadbeef"
    assert saved.owner_name == "Batch processor"
    assert saved.is_active is False


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_update_can_rotate_key_hash(session: AsyncSession) -> None:
    repo = APIKeyRepositoryImpl(session)
    key = await repo.add(_key(id="ak-rotate"))
    rotated = APIKey(
        id=key.id,
        key_hash="argon2$newhash",
        owner_name=key.owner_name,
        is_active=key.is_active,
    )
    updated = await repo.update(rotated)
    assert updated.key_hash == "argon2$newhash"
    # get_by_hash should find the new hash
    found = await repo.get_by_hash("argon2$newhash")
    assert found is not None


@pytest.mark.integration
async def test_update_can_change_owner_name(session: AsyncSession) -> None:
    repo = APIKeyRepositoryImpl(session)
    key = await repo.add(_key(id="ak-owner"))
    reassigned = APIKey(
        id=key.id,
        key_hash=key.key_hash,
        owner_name="New department",
        is_active=key.is_active,
    )
    updated = await repo.update(reassigned)
    assert updated.owner_name == "New department"


@pytest.mark.integration
async def test_update_can_revoke_key(session: AsyncSession) -> None:
    repo = APIKeyRepositoryImpl(session)
    key = await repo.add(_key(id="ak-revoke", is_active=True))
    revoked = APIKey(
        id=key.id,
        key_hash=key.key_hash,
        owner_name=key.owner_name,
        is_active=False,
    )
    updated = await repo.update(revoked)
    assert updated.is_active is False
    # list_active should no longer include this key
    active = await repo.list_active()
    assert all(k.id != "ak-revoke" for k in active)


@pytest.mark.integration
async def test_update_can_reactivate_key(session: AsyncSession) -> None:
    repo = APIKeyRepositoryImpl(session)
    key = await repo.add(_key(id="ak-reactivate", is_active=False))
    reactivated = APIKey(
        id=key.id,
        key_hash=key.key_hash,
        owner_name=key.owner_name,
        is_active=True,
    )
    updated = await repo.update(reactivated)
    assert updated.is_active is True
    active = await repo.list_active()
    assert any(k.id == "ak-reactivate" for k in active)
