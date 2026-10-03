"""Integration tests for AuditLogRepositoryImpl.

AuditLogEntry is append-only — no update method.
Covers: get_by_id (hit/miss), add (round-trip of all fields), multiple
entries from the same actor, entries from different actors.
"""

from __future__ import annotations
import pytest

from typing import TYPE_CHECKING

from domain.entities.audit_log_entry import AuditLogEntry
from infrastructure.db.repositories import AuditLogRepositoryImpl

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.ext.asyncio import AsyncSession


def _entry(
    *,
    id: str,
    actor: str = "admin_muzzammil",
    action: str = "ZONE_THRESHOLD_UPDATE",
    target: str = "zone-kalam",
    now: datetime,
) -> AuditLogEntry:
    return AuditLogEntry(
        id=id,
        actor_username=actor,
        action=action,
        target=target,
        timestamp=now,
    )


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


async def test_get_by_id_returns_entry(
    session: AsyncSession, now: datetime
) -> None:
    repo = AuditLogRepositoryImpl(session)
    entry = _entry(id="al-1", now=now)
    await repo.add(entry)
    found = await repo.get_by_id("al-1")
    assert found is not None
    assert found.id == "al-1"
    assert found.actor_username == "admin_muzzammil"
    assert found.action == "ZONE_THRESHOLD_UPDATE"
    assert found.target == "zone-kalam"


@pytest.mark.integration
async def test_get_by_id_returns_none_for_unknown(session: AsyncSession) -> None:
    repo = AuditLogRepositoryImpl(session)
    assert await repo.get_by_id("no-such-entry") is None


# ---------------------------------------------------------------------------
# add — field round-trip
# ---------------------------------------------------------------------------


async def test_add_roundtrips_all_fields(
    session: AsyncSession, now: datetime
) -> None:
    repo = AuditLogRepositoryImpl(session)
    entry = AuditLogEntry(
        id="al-full",
        actor_username="responder_ayesha",
        action="COMMUNITY_REPORT_APPROVED",
        target="report-xyz",
        timestamp=now,
    )
    saved = await repo.add(entry)
    assert saved.id == "al-full"
    assert saved.actor_username == "responder_ayesha"
    assert saved.action == "COMMUNITY_REPORT_APPROVED"
    assert saved.target == "report-xyz"


# ---------------------------------------------------------------------------
# multiple entries — persistence of each is independent
# ---------------------------------------------------------------------------


async def test_multiple_entries_each_retrievable(
    session: AsyncSession, now: datetime
) -> None:
    repo = AuditLogRepositoryImpl(session)
    ids = ["al-a", "al-b", "al-c"]
    for eid in ids:
        await repo.add(_entry(id=eid, now=now))
    for eid in ids:
        found = await repo.get_by_id(eid)
        assert found is not None, f"Entry {eid!r} not found"
        assert found.id == eid


async def test_entries_from_different_actors_coexist(
    session: AsyncSession, now: datetime
) -> None:
    repo = AuditLogRepositoryImpl(session)
    await repo.add(_entry(id="al-admin", actor="admin_muzzammil", now=now))
    await repo.add(_entry(id="al-resp", actor="responder_bilal", now=now))
    admin_entry = await repo.get_by_id("al-admin")
    resp_entry = await repo.get_by_id("al-resp")
    assert admin_entry is not None
    assert resp_entry is not None
    assert admin_entry.actor_username == "admin_muzzammil"
    assert resp_entry.actor_username == "responder_bilal"
