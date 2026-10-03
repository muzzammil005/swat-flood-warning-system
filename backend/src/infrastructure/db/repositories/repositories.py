"""SQLAlchemy 2.0 async implementations of the 12 repository ports.

Pattern used by every implementation:

1. Accept an :class:`sqlalchemy.ext.asyncio.AsyncSession` in the constructor
   (injected by Stage 4's FastAPI dependency or an integration test). The
   session-scoped transaction boundary is the caller's responsibility — this
   module never calls ``commit``/``rollback``/``begin`` on its own.
2. Construct an ORM model via :mod:`infrastructure.db.mappers`, pass it to
   ``session.add`` / ``session.execute(select(...))``, and map any row(s)
   back to the domain entity before returning.
3. For ``update`` on mutable repos, we do a load→mutate ORM fields→flush dance
   inside the same session. Because ``session`` already has ``expire_on_commit=False``
   (see :mod:`infrastructure.db.session`), the caller can safely read the
   returned entity even after the outer transaction commits.

The append-only contract (SensorReading, WeatherSnapshot, RiskAssessment, Alert,
AuditLogEntry) is enforced structurally here: those 5 classes simply don't have
an ``update`` method — trying to call one is a ``AttributeError`` at the call
site rather than a runtime ``NotImplementedError``.
"""

from __future__ import annotations

from collections.abc import Callable  # noqa: TC003 — _one_or_none uses Callable at runtime
from typing import TYPE_CHECKING, TypeVar

from sqlalchemy import select

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.mappers import (
    alert_to_domain,
    alert_to_orm,
    api_key_to_domain,
    api_key_to_orm,
    audit_log_entry_to_domain,
    audit_log_entry_to_orm,
    community_report_to_domain,
    community_report_to_orm,
    inventory_item_to_domain,
    inventory_item_to_orm,
    manual_override_to_domain,
    manual_override_to_orm,
    resource_center_to_domain,
    resource_center_to_orm,
    risk_assessment_to_domain,
    risk_assessment_to_orm,
    sensor_reading_to_domain,
    sensor_reading_to_orm,
    user_to_domain,
    user_to_orm,
    weather_snapshot_to_domain,
    weather_snapshot_to_orm,
    _ZONE_TERRAIN_FEATURE_FIELDS,
    zone_terrain_features_to_dict,
    zone_terrain_features_to_orm,
    zone_thresholds_to_domain,
    zone_thresholds_to_orm,
    zone_to_domain,
    zone_to_orm,
)
from infrastructure.db.models import (
    AlertModel,
    APIKeyModel,
    AuditLogEntryModel,
    CommunityReportModel,
    DBCommunityReportStatus,
    DBUserRole,
    InventoryItemModel,
    ManualOverrideModel,
    ResourceCenterModel,
    RiskAssessmentModel,
    SensorReadingModel,
    UserModel,
    WeatherSnapshotModel,
    ZoneModel,
    ZoneTerrainFeaturesModel,
    ZoneThresholdsModel,
)

if TYPE_CHECKING:
    from domain.entities.alert import Alert
    from domain.entities.api_key import APIKey
    from domain.entities.audit_log_entry import AuditLogEntry
    from domain.entities.community_report import CommunityReport
    from domain.entities.inventory_item import InventoryItem
    from domain.entities.manual_override import ManualOverride
    from domain.entities.resource_center import ResourceCenter
    from domain.entities.risk_assessment import RiskAssessment
    from domain.entities.sensor_reading import SensorReading
    from domain.entities.user import User
    from domain.entities.weather_snapshot import WeatherSnapshot
    from domain.entities.zone import Zone
    from domain.value_objects.zone_thresholds import ZoneThresholds


T = TypeVar("T")
U = TypeVar("U")


def _one_or_none(row: T | None, mapper: Callable[[T], U]) -> U | None:
    """Apply a ``*_to_domain`` mapper to a single ORM row or None."""
    if row is None:
        return None
    return mapper(row)


class SensorReadingRepositoryImpl:
    """Persistent water-level observations — INSERT-only."""

    def __init__(self, session: AsyncSession, /) -> None:
        self._session = session

    async def get_by_id(self, reading_id: str, /) -> SensorReading | None:
        stmt = select(SensorReadingModel).where(SensorReadingModel.id == reading_id)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return _one_or_none(row, sensor_reading_to_domain)

    async def list_for_zone(
        self, zone_id: str, /, *, limit: int = 100
    ) -> list[SensorReading]:
        stmt = (
            select(SensorReadingModel)
            .where(SensorReadingModel.zone_id == zone_id)
            .order_by(SensorReadingModel.timestamp.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [sensor_reading_to_domain(r) for r in rows]

    async def add(self, reading: SensorReading, /) -> SensorReading:
        orm = sensor_reading_to_orm(reading)
        self._session.add(orm)
        await self._session.flush()
        return sensor_reading_to_domain(orm)


class WeatherSnapshotRepositoryImpl:
    """Weather-provider snapshot store — append-only."""

    def __init__(self, session: AsyncSession, /) -> None:
        self._session = session

    async def get_by_id(self, snapshot_id: str, /) -> WeatherSnapshot | None:
        stmt = select(WeatherSnapshotModel).where(WeatherSnapshotModel.id == snapshot_id)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return _one_or_none(row, weather_snapshot_to_domain)

    async def latest_for_zone(self, zone_id: str, /) -> WeatherSnapshot | None:
        stmt = (
            select(WeatherSnapshotModel)
            .where(WeatherSnapshotModel.zone_id == zone_id)
            .order_by(WeatherSnapshotModel.fetched_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return _one_or_none(row, weather_snapshot_to_domain)

    async def add(self, snapshot: WeatherSnapshot, /) -> WeatherSnapshot:
        orm = weather_snapshot_to_orm(snapshot)
        self._session.add(orm)
        await self._session.flush()
        return weather_snapshot_to_domain(orm)

    async def list_for_zone_in_window(
        self, zone_id: str, /, *, start_time: datetime
    ) -> list[WeatherSnapshot]:
        """List weather snapshots for a zone within a time window.
        
        Used for rainfall vs risk charts.
        """
        stmt = (
            select(WeatherSnapshotModel)
            .where(WeatherSnapshotModel.zone_id == zone_id)
            .where(WeatherSnapshotModel.fetched_at >= start_time)
            .order_by(WeatherSnapshotModel.fetched_at.asc())
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [weather_snapshot_to_domain(r) for r in rows]


class RiskAssessmentRepositoryImpl:
    """Risk-engine outputs per zone per cycle — append-only history."""

    def __init__(self, session: AsyncSession, /) -> None:
        self._session = session

    async def get_by_id(self, assessment_id: str, /) -> RiskAssessment | None:
        stmt = select(RiskAssessmentModel).where(RiskAssessmentModel.id == assessment_id)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return _one_or_none(row, risk_assessment_to_domain)

    async def latest_for_zone(self, zone_id: str, /) -> RiskAssessment | None:
        stmt = (
            select(RiskAssessmentModel)
            .where(RiskAssessmentModel.zone_id == zone_id)
            .order_by(RiskAssessmentModel.computed_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return _one_or_none(row, risk_assessment_to_domain)

    async def history_for_zone(
        self, zone_id: str, /, *, limit: int = 50
    ) -> list[RiskAssessment]:
        stmt = (
            select(RiskAssessmentModel)
            .where(RiskAssessmentModel.zone_id == zone_id)
            .order_by(RiskAssessmentModel.computed_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [risk_assessment_to_domain(r) for r in rows]

    async def list_for_zone_in_window(
        self, zone_id: str, /, *, start_time: datetime
    ) -> list[RiskAssessment]:
        stmt = (
            select(RiskAssessmentModel)
            .where(
                RiskAssessmentModel.zone_id == zone_id,
                RiskAssessmentModel.computed_at >= start_time,
            )
            .order_by(RiskAssessmentModel.computed_at.asc())
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [risk_assessment_to_domain(r) for r in rows]

    async def add(self, assessment: RiskAssessment, /) -> RiskAssessment:
        orm = risk_assessment_to_orm(assessment)
        self._session.add(orm)
        await self._session.flush()
        return risk_assessment_to_domain(orm)


class AlertRepositoryImpl:
    """CAP-inspired alerts append-only; corrections = new rows."""

    def __init__(self, session: AsyncSession, /) -> None:
        self._session = session

    async def get_by_id(self, alert_id: str, /) -> Alert | None:
        stmt = select(AlertModel).where(AlertModel.id == alert_id)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return _one_or_none(row, alert_to_domain)

    async def list_active(self, *, limit: int = 50) -> list[Alert]:
        stmt = select(AlertModel).order_by(AlertModel.sent_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [alert_to_domain(r) for r in rows]

    async def add(self, alert: Alert, /) -> Alert:
        orm = alert_to_orm(alert)
        self._session.add(orm)
        await self._session.flush()
        return alert_to_domain(orm)


class AuditLogRepositoryImpl:
    """Write-mostly-read-rarely audit trail — append-only."""

    def __init__(self, session: AsyncSession, /) -> None:
        self._session = session

    async def get_by_id(self, entry_id: str, /) -> AuditLogEntry | None:
        stmt = select(AuditLogEntryModel).where(AuditLogEntryModel.id == entry_id)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return _one_or_none(row, audit_log_entry_to_domain)

    async def add(self, entry: AuditLogEntry, /) -> AuditLogEntry:
        orm = audit_log_entry_to_orm(entry)
        self._session.add(orm)
        await self._session.flush()
        return audit_log_entry_to_domain(orm)


class ZoneRepositoryImpl:
    """River network zones — mutable (name, coords, upstream edge)."""

    def __init__(self, session: AsyncSession, /) -> None:
        self._session = session

    async def get_by_id(self, zone_id: str, /) -> Zone | None:
        stmt = select(ZoneModel).where(ZoneModel.id == zone_id)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return _one_or_none(row, zone_to_domain)

    async def get_by_name(self, name: str, /) -> Zone | None:
        stmt = select(ZoneModel).where(ZoneModel.name == name)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return _one_or_none(row, zone_to_domain)

    async def find_nearest(self, latitude: float, longitude: float, /) -> Zone | None:
        from sqlalchemy.sql import text
        point_wkt = f"POINT({longitude} {latitude})"
        stmt = text("""
            SELECT id
            FROM zones
            ORDER BY coordinates <-> ST_GeogFromText(:point)
            LIMIT 1
        """).bindparams(point=point_wkt)
        result = await self._session.execute(stmt)
        row = result.first()
        if not row:
            return None
        return await self.get_by_id(row.id)

    async def list_all(self) -> list[Zone]:
        stmt = select(ZoneModel).order_by(ZoneModel.name.asc())
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [zone_to_domain(r) for r in rows]

    async def add(self, zone: Zone, /) -> Zone:
        orm = zone_to_orm(zone)
        self._session.add(orm)
        await self._session.flush()
        return zone_to_domain(orm)

    async def update(self, zone: Zone, /) -> Zone:
        stmt = select(ZoneModel).where(ZoneModel.id == zone.id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one()
        fresh = zone_to_orm(zone)
        orm.name = fresh.name
        orm.coordinates = fresh.coordinates
        orm.upstream_zone_id = fresh.upstream_zone_id
        await self._session.flush()
        return zone_to_domain(orm)


class ZoneThresholdsRepositoryImpl:
    """Per-zone calibration knobs — one row per zone, upsert semantics."""

    def __init__(self, session: AsyncSession, /) -> None:
        self._session = session

    async def get_by_zone_id(self, zone_id: str, /) -> ZoneThresholds | None:
        stmt = select(ZoneThresholdsModel).where(ZoneThresholdsModel.zone_id == zone_id)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return _one_or_none(row, zone_thresholds_to_domain)

    async def upsert(
        self, zone_id: str, thresholds: ZoneThresholds, /
    ) -> ZoneThresholds:
        stmt = select(ZoneThresholdsModel).where(ZoneThresholdsModel.zone_id == zone_id)
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing is None:
            orm = zone_thresholds_to_orm(thresholds, zone_id=zone_id)
            self._session.add(orm)
            await self._session.flush()
            return zone_thresholds_to_domain(orm)
        fresh = zone_thresholds_to_orm(thresholds, zone_id=zone_id, id=existing.id)
        existing.water_warning_level_cm = fresh.water_warning_level_cm
        existing.water_critical_level_cm = fresh.water_critical_level_cm
        existing.heavy_rain_threshold_mm = fresh.heavy_rain_threshold_mm
        await self._session.flush()
        return zone_thresholds_to_domain(existing)


class CommunityReportRepositoryImpl:
    """Civilian ground-truth reports — only status is mutable."""

    def __init__(self, session: AsyncSession, /) -> None:
        self._session = session

    async def get_by_id(self, report_id: str, /) -> CommunityReport | None:
        stmt = select(CommunityReportModel).where(CommunityReportModel.id == report_id)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return _one_or_none(row, community_report_to_domain)

    async def list_pending(self, *, limit: int = 50) -> list[CommunityReport]:
        stmt = (
            select(CommunityReportModel)
            .where(CommunityReportModel.status == DBCommunityReportStatus.Pending)
            .order_by(CommunityReportModel.submitted_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [community_report_to_domain(r) for r in rows]

    async def list_for_zone(
        self, zone_id: str, /, *, limit: int = 50
    ) -> list[CommunityReport]:
        stmt = (
            select(CommunityReportModel)
            .where(CommunityReportModel.zone_id == zone_id)
            .order_by(CommunityReportModel.submitted_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [community_report_to_domain(r) for r in rows]

    async def list_with_filters(
        self, *, status: str | None = None, zone_id: str | None = None, limit: int = 100
    ) -> list[CommunityReport]:
        stmt = select(CommunityReportModel)
        where_clauses = []
        if status is not None:
            where_clauses.append(CommunityReportModel.status == DBCommunityReportStatus(status))
        if zone_id is not None:
            where_clauses.append(CommunityReportModel.zone_id == zone_id)
            
        if where_clauses:
            stmt = stmt.where(*where_clauses)
            
        stmt = stmt.order_by(CommunityReportModel.submitted_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [community_report_to_domain(r) for r in rows]

    async def add(self, report: CommunityReport, /) -> CommunityReport:
        orm = community_report_to_orm(report)
        self._session.add(orm)
        await self._session.flush()
        return community_report_to_domain(orm)

    async def update_status(
        self, report: CommunityReport, /, *, new_status: str
    ) -> CommunityReport:
        stmt = select(CommunityReportModel).where(CommunityReportModel.id == report.id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one()
        orm.status = DBCommunityReportStatus(new_status)
        await self._session.flush()
        return community_report_to_domain(orm)


class ManualOverrideRepositoryImpl:
    """Admin-signed forced risk tiers — mutable (e.g. revoke)."""

    def __init__(self, session: AsyncSession, /) -> None:
        self._session = session

    async def get_by_id(self, override_id: str, /) -> ManualOverride | None:
        stmt = select(ManualOverrideModel).where(ManualOverrideModel.id == override_id)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return _one_or_none(row, manual_override_to_domain)

    async def active_for_zone(self, zone_id: str, /) -> ManualOverride | None:
        stmt = (
            select(ManualOverrideModel)
            .where(ManualOverrideModel.zone_id == zone_id)
            .order_by(ManualOverrideModel.timestamp.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return _one_or_none(row, manual_override_to_domain)

    async def add(self, override: ManualOverride, /) -> ManualOverride:
        orm = manual_override_to_orm(override)
        self._session.add(orm)
        await self._session.flush()
        return manual_override_to_domain(orm)

    async def update(self, override: ManualOverride, /) -> ManualOverride:
        stmt = select(ManualOverrideModel).where(ManualOverrideModel.id == override.id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one()
        fresh = manual_override_to_orm(override)
        orm.zone_id = fresh.zone_id
        orm.threat_level = fresh.threat_level
        orm.reason = fresh.reason
        orm.admin_username = fresh.admin_username
        orm.timestamp = fresh.timestamp
        await self._session.flush()
        return manual_override_to_domain(orm)


class ResourceCenterRepositoryImpl:
    """Depot/staging-area catalog — mutable name and location_zone."""

    def __init__(self, session: AsyncSession, /) -> None:
        self._session = session

    async def get_by_id(self, center_id: str, /) -> ResourceCenter | None:
        stmt = select(ResourceCenterModel).where(ResourceCenterModel.id == center_id)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return _one_or_none(row, resource_center_to_domain)

    async def list_all(self) -> list[ResourceCenter]:
        stmt = select(ResourceCenterModel).order_by(ResourceCenterModel.name.asc())
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [resource_center_to_domain(r) for r in rows]

    async def list_for_zone(self, zone_id: str, /) -> list[ResourceCenter]:
        stmt = (
            select(ResourceCenterModel)
            .where(ResourceCenterModel.location_zone == zone_id)
            .order_by(ResourceCenterModel.name.asc())
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [resource_center_to_domain(r) for r in rows]

    async def add(self, center: ResourceCenter, /) -> ResourceCenter:
        orm = resource_center_to_orm(center)
        self._session.add(orm)
        await self._session.flush()
        return resource_center_to_domain(orm)

    async def update(self, center: ResourceCenter, /) -> ResourceCenter:
        stmt = select(ResourceCenterModel).where(ResourceCenterModel.id == center.id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one()
        fresh = resource_center_to_orm(center)
        orm.name = fresh.name
        orm.location_zone = fresh.location_zone
        await self._session.flush()
        return resource_center_to_domain(orm)


class InventoryItemRepositoryImpl:
    """SKU rows inside a ResourceCenter — quantity is the hot mutable field."""

    def __init__(self, session: AsyncSession, /) -> None:
        self._session = session

    async def get_by_id(self, item_id: str, /) -> InventoryItem | None:
        stmt = select(InventoryItemModel).where(InventoryItemModel.id == item_id)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return _one_or_none(row, inventory_item_to_domain)

    async def list_for_center(self, center_id: str, /) -> list[InventoryItem]:
        stmt = (
            select(InventoryItemModel)
            .where(InventoryItemModel.center_id == center_id)
            .order_by(InventoryItemModel.item_name.asc())
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [inventory_item_to_domain(r) for r in rows]

    async def add(self, item: InventoryItem, /) -> InventoryItem:
        orm = inventory_item_to_orm(item)
        self._session.add(orm)
        await self._session.flush()
        return inventory_item_to_domain(orm)

    async def update(self, item: InventoryItem, /) -> InventoryItem:
        stmt = select(InventoryItemModel).where(InventoryItemModel.id == item.id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one()
        fresh = inventory_item_to_orm(item)
        orm.item_name = fresh.item_name
        orm.quantity = fresh.quantity
        orm.center_id = fresh.center_id
        await self._session.flush()
        return inventory_item_to_domain(orm)


class UserRepositoryImpl:
    """Operator accounts — role, password_hash, username all mutable."""

    def __init__(self, session: AsyncSession, /) -> None:
        self._session = session

    async def get_by_id(self, user_id: str, /) -> User | None:
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return _one_or_none(row, user_to_domain)

    async def get_by_username(self, username: str, /) -> User | None:
        stmt = select(UserModel).where(UserModel.username == username)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return _one_or_none(row, user_to_domain)

    async def list_all(self) -> list[User]:
        stmt = select(UserModel).order_by(UserModel.username.asc())
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [user_to_domain(r) for r in rows]

    async def add(self, user: User, /) -> User:
        orm = user_to_orm(user)
        self._session.add(orm)
        await self._session.flush()
        return user_to_domain(orm)

    async def update(self, user: User, /) -> User:
        stmt = select(UserModel).where(UserModel.id == user.id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one()
        # Update only mutable domain fields, preserve infrastructure-only columns
        orm.username = user.username
        orm.role = DBUserRole(user.role)
        # Do NOT touch password_hash or created_at - they're infrastructure-only
        await self._session.flush()
        return user_to_domain(orm)


class APIKeyRepositoryImpl:
    """M2M credential hashes — is_active toggle = revocation path."""

    def __init__(self, session: AsyncSession, /) -> None:
        self._session = session

    async def get_by_id(self, key_id: str, /) -> APIKey | None:
        stmt = select(APIKeyModel).where(APIKeyModel.id == key_id)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return _one_or_none(row, api_key_to_domain)

    async def get_by_hash(self, key_hash: str, /) -> APIKey | None:
        stmt = select(APIKeyModel).where(APIKeyModel.key_hash == key_hash)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return _one_or_none(row, api_key_to_domain)

    async def list_active(self) -> list[APIKey]:
        stmt = (
            select(APIKeyModel)
            .where(APIKeyModel.is_active.is_(True))
            .order_by(APIKeyModel.owner_name.asc())
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [api_key_to_domain(r) for r in rows]

    async def add(self, api_key: APIKey, /) -> APIKey:
        orm = api_key_to_orm(api_key)
        self._session.add(orm)
        await self._session.flush()
        return api_key_to_domain(orm)

    async def update(self, api_key: APIKey, /) -> APIKey:
        stmt = select(APIKeyModel).where(APIKeyModel.id == api_key.id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one()
        fresh = api_key_to_orm(api_key)
        orm.key_hash = fresh.key_hash
        orm.owner_name = fresh.owner_name
        orm.is_active = fresh.is_active
        await self._session.flush()
        return api_key_to_domain(orm)


class ZoneTerrainFeaturesRepositoryImpl:
    """Static ML terrain features per zone — upsert semantics, one row per zone.

    Returns plain feature dicts (not a domain VO) because these rows are
    infrastructure-only inputs to the ML predictor, never surfaced to the
    domain layer.
    """

    def __init__(self, session: AsyncSession, /) -> None:
        self._session = session

    async def get_by_zone_id(self, zone_id: str, /) -> dict[str, float | int] | None:
        stmt = select(ZoneTerrainFeaturesModel).where(
            ZoneTerrainFeaturesModel.zone_id == zone_id
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return zone_terrain_features_to_dict(row)

    async def upsert(
        self, zone_id: str, features: dict[str, float | int], /
    ) -> dict[str, float | int]:
        stmt = select(ZoneTerrainFeaturesModel).where(
            ZoneTerrainFeaturesModel.zone_id == zone_id
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing is None:
            orm = zone_terrain_features_to_orm(features, zone_id=zone_id)
            self._session.add(orm)
            await self._session.flush()
            return zone_terrain_features_to_dict(orm)
        # Overwrite all 22 feature columns on the existing row.
        fresh = zone_terrain_features_to_orm(features, zone_id=zone_id, id=existing.id)
        for field in _ZONE_TERRAIN_FEATURE_FIELDS:
            setattr(existing, field, getattr(fresh, field))
        await self._session.flush()
        return zone_terrain_features_to_dict(existing)
