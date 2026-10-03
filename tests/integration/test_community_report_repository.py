"""Integration tests for CommunityReportRepositoryImpl.

Status is the only mutable field — update_status transitions.
Covers: get_by_id (hit/miss), list_pending (filtering, ordering, limit),
list_for_zone (ordering, limit, cross-zone isolation), add (round-trip of
all three statuses), update_status (Pending→Approved, Approved→Rejected,
no duplicate transition allowed for immutable observation field).
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

import pytest

from domain.entities.community_report import CommunityReport
from domain.entities.zone import Zone
from infrastructure.db.repositories import CommunityReportRepositoryImpl

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.ext.asyncio import AsyncSession


def _report(
    *,
    id: str,
    zone_id: str,
    observation: str = "Water rising near bridge",
    status: str = "Pending",
    ts_offset_seconds: int = 0,
    now: datetime,
) -> CommunityReport:
    return CommunityReport(
        id=id,
        zone_id=zone_id,
        observation=observation,
        status=status,  # type: ignore[arg-type]
        submitted_at=now + timedelta(seconds=ts_offset_seconds),
    )


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


async def test_get_by_id_returns_report(
    session: AsyncSession, zone_a: Zone, now: datetime
) -> None:
    repo = CommunityReportRepositoryImpl(session)
    await repo.add(_report(id="cr-1", zone_id=zone_a.id, now=now))
    found = await repo.get_by_id("cr-1")
    assert found is not None
    assert found.zone_id == zone_a.id
    assert found.observation == "Water rising near bridge"
    assert found.status == "Pending"


@pytest.mark.integration
async def test_get_by_id_returns_none_for_unknown(session: AsyncSession) -> None:
    repo = CommunityReportRepositoryImpl(session)
    assert await repo.get_by_id("no-such-report") is None


# ---------------------------------------------------------------------------
# list_pending
# ---------------------------------------------------------------------------


async def test_list_pending_filters_by_status(
    session: AsyncSession, zone_a: Zone, now: datetime
) -> None:
    repo = CommunityReportRepositoryImpl(session)
    await repo.add(_report(id="cr-pend", zone_id=zone_a.id, status="Pending", now=now))
    await repo.add(_report(id="cr-appr", zone_id=zone_a.id, status="Approved", now=now))
    pending = await repo.list_pending()
    assert len(pending) == 1
    assert pending[0].id == "cr-pend"


async def test_list_pending_orders_desc_by_submitted_at(
    session: AsyncSession, zone_a: Zone, now: datetime
) -> None:
    repo = CommunityReportRepositoryImpl(session)
    for i in range(3):
        await repo.add(_report(id=f"cr-{i}", zone_id=zone_a.id, ts_offset_seconds=i * 30, now=now))
    pending = await repo.list_pending()
    timestamps = [r.submitted_at for r in pending]
    assert timestamps == sorted(timestamps, reverse=True)


async def test_list_pending_respects_limit(
    session: AsyncSession, zone_a: Zone, now: datetime
) -> None:
    repo = CommunityReportRepositoryImpl(session)
    for i in range(5):
        await repo.add(_report(id=f"cr-lim-{i}", zone_id=zone_a.id, now=now))
    assert len(await repo.list_pending(limit=2)) == 2


@pytest.mark.integration
async def test_list_pending_empty_when_no_pending(session: AsyncSession) -> None:
    repo = CommunityReportRepositoryImpl(session)
    assert await repo.list_pending() == []


# ---------------------------------------------------------------------------
# list_for_zone
# ---------------------------------------------------------------------------


async def test_list_for_zone_returns_only_for_that_zone(
    session: AsyncSession, zone_a: Zone, zone_b: Zone, now: datetime
) -> None:
    repo = CommunityReportRepositoryImpl(session)
    await repo.add(_report(id="cr-a", zone_id=zone_a.id, now=now))
    await repo.add(_report(id="cr-b", zone_id=zone_b.id, now=now))
    reports_a = await repo.list_for_zone(zone_a.id)
    assert len(reports_a) == 1
    assert reports_a[0].id == "cr-a"


async def test_list_for_zone_orders_desc_by_submitted_at(
    session: AsyncSession, zone_a: Zone, now: datetime
) -> None:
    repo = CommunityReportRepositoryImpl(session)
    for i in range(3):
        await repo.add(_report(id=f"cr-ord-{i}", zone_id=zone_a.id, ts_offset_seconds=i * 10, now=now))
    reports = await repo.list_for_zone(zone_a.id)
    timestamps = [r.submitted_at for r in reports]
    assert timestamps == sorted(timestamps, reverse=True)


async def test_list_for_zone_respects_limit(
    session: AsyncSession, zone_a: Zone, now: datetime
) -> None:
    repo = CommunityReportRepositoryImpl(session)
    for i in range(5):
        await repo.add(_report(id=f"cr-lz-{i}", zone_id=zone_a.id, now=now))
    assert len(await repo.list_for_zone(zone_a.id, limit=3)) == 3


# ---------------------------------------------------------------------------
# add — all three statuses round-trip
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("status", ["Pending", "Approved", "Rejected"])
async def test_all_statuses_roundtrip(
    session: AsyncSession, zone_a: Zone, now: datetime, status: str
) -> None:
    repo = CommunityReportRepositoryImpl(session)
    report = _report(id="cr-status", zone_id=zone_a.id, status=status, now=now)
    saved = await repo.add(report)
    assert saved.status == status


# ---------------------------------------------------------------------------
# update_status
# ---------------------------------------------------------------------------


async def test_update_status_pending_to_approved(
    session: AsyncSession, zone_a: Zone, now: datetime
) -> None:
    repo = CommunityReportRepositoryImpl(session)
    report = await repo.add(_report(id="cr-mod", zone_id=zone_a.id, now=now))
    updated = await repo.update_status(report, new_status="Approved")
    assert updated.status == "Approved"
    fetched = await repo.get_by_id("cr-mod")
    assert fetched is not None
    assert fetched.status == "Approved"


async def test_update_status_approved_to_rejected(
    session: AsyncSession, zone_a: Zone, now: datetime
) -> None:
    repo = CommunityReportRepositoryImpl(session)
    report = await repo.add(_report(id="cr-mod2", zone_id=zone_a.id, status="Approved", now=now))
    updated = await repo.update_status(report, new_status="Rejected")
    assert updated.status == "Rejected"


async def test_update_status_does_not_mutate_observation(
    session: AsyncSession, zone_a: Zone, now: datetime
) -> None:
    repo = CommunityReportRepositoryImpl(session)
    original_obs = "Water at bridge footings"
    report = await repo.add(_report(id="cr-obs", zone_id=zone_a.id, observation=original_obs, now=now))
    await repo.update_status(report, new_status="Approved")
    fetched = await repo.get_by_id("cr-obs")
    assert fetched is not None
    assert fetched.observation == original_obs
