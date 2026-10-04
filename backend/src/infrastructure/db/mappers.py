"""Pure mapper functions between ORM models and domain entities.

Every function in this module is side-effect-free: no DB connections, no
Redis, no HTTP — just construct a new object on one side from fields on the
other. The repository layer (Prompt 4) is the glue that calls these at the
boundary.

Key round-trip gotchas handled here:

1. **Coordinates (domain) ↔ Geography(Point, 4326) (ORM):** GeoAlchemy2 uses
   ``ST_SetSRID(ST_MakePoint(lon, lat), 4326)`` (x=lon, y=lat per the OGC
   standard) but our domain :class:`Coordinates` stores latitude first
   (standard "lat/lon" conversation order). We swap axes in both directions.
   We use the ``shapely`` + ``geoalchemy2.shape`` bridge for round-tripping.

2. **RiskTier (domain IntEnum) ↔ DBRiskTier (native Postgres ENUM):** The DB
   enum stores string names ("LOW", "MEDIUM", ...). Both enums share the
   exact same member identifiers so round-tripping is via ``.name``.

3. **Domain entities without an ``id`` (WeatherSnapshot, RiskAssessment, Alert).**
   These three entities are "historical facts" in the domain — they don't
   carry a database primary key in their constructor. The ORM model *does*
   have an ``id`` PK column (every table needs one); the mapper simply
   omits it when building the domain entity, and generates a UUID when
   writing back (repository is responsible for persisting it).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, TypeVar, cast

from geoalchemy2 import WKBElement, WKTElement
from geoalchemy2.shape import to_shape

from infrastructure.db.models import (
    AlertModel,
    APIKeyModel,
    AuditLogEntryModel,
    CommunityReportModel,
    DBCommunityReportStatus,
    DBRiskTier,
    DBSensorSource,
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

_ZONE_TERRAIN_FEATURE_FIELDS: tuple[str, ...] = (
    "elevation",
    "slope",
    "stream_proximity",
    "drainage_density",
    "upstream_area",
    "hand",
    "landcover_encoded",
    "ndvi",
    "rain_jan",
    "rain_feb",
    "rain_mar",
    "rain_apr",
    "rain_may",
    "rain_jun",
    "rain_jul",
    "rain_aug",
    "rain_sep",
    "rain_oct",
    "rain_nov",
    "rain_dec",
    "longitude",
    "latitude",
)

if TYPE_CHECKING:
    from shapely.geometry import Point as _Point

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
    from domain.value_objects.coordinates import Coordinates
    from domain.value_objects.zone_thresholds import ZoneThresholds

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _enum_name_to_domain(
    db_enum_member: object,
    domain_enum_cls: type[T],
) -> T:
    """Map a DB native-enum member → a domain enum member via shared ``.name`` or ``.value``."""
    if hasattr(db_enum_member, "name"):
        name = str(db_enum_member.name).upper()
    elif hasattr(db_enum_member, "value") and isinstance(db_enum_member.value, str):
        name = str(db_enum_member.value).upper()
    elif isinstance(db_enum_member, str):
        name = db_enum_member.upper()
    elif isinstance(db_enum_member, int):
        return domain_enum_cls(db_enum_member)
    else:
        name = getattr(db_enum_member, "name", None)
        if name is None:  # pragma: no cover — defensive
            raise TypeError(f"Expected a DB enum instance, got {type(db_enum_member)!r}")
        name = str(name).upper()

    if hasattr(domain_enum_cls, name):
        return cast("T", getattr(domain_enum_cls, name))
    if name in getattr(domain_enum_cls, "__members__", {}):
        return cast("T", domain_enum_cls[name])
    try:
        return domain_enum_cls(name)
    except (ValueError, TypeError):
        pass
    raise TypeError(f"Cannot map {db_enum_member!r} to domain enum {domain_enum_cls}")


def _domain_enum_to_db(
    domain_enum_member: object,
    db_enum_cls: type[T],
) -> T:
    """Map a domain enum member → DB native-enum member via shared ``.name`` or ``.value``."""
    if hasattr(domain_enum_member, "name"):
        name = str(domain_enum_member.name).upper()
    elif hasattr(domain_enum_member, "value") and isinstance(domain_enum_member.value, str):
        name = str(domain_enum_member.value).upper()
    elif isinstance(domain_enum_member, str):
        name = domain_enum_member.upper()
    else:
        name = getattr(domain_enum_member, "name", None)
        if name is None:  # pragma: no cover — defensive
            raise TypeError(f"Expected a domain enum instance, got {type(domain_enum_member)!r}")
        name = str(name).upper()

    if hasattr(db_enum_cls, name):
        return cast("T", getattr(db_enum_cls, name))
    if name in getattr(db_enum_cls, "__members__", {}):
        return cast("T", db_enum_cls[name])
    try:
        return db_enum_cls(name)
    except (ValueError, TypeError):
        pass
    raise TypeError(f"Cannot map {domain_enum_member!r} to DB enum {db_enum_cls}")


def _coords_to_wkb(coordinates: Coordinates) -> WKTElement:
    """Convert a domain Coordinates (lat, lon) → GeoAlchemy2 Geography(Point)."""
    return WKTElement(
        f"POINT({coordinates.longitude} {coordinates.latitude})",
        srid=4326,
    )


def _wkb_to_coords(geometry: object) -> Coordinates:
    """Convert a GeoAlchemy2 Geography(Point) column → domain Coordinates (lat, lon)."""


    from domain.value_objects.coordinates import Coordinates

    cast_geom = cast("WKBElement | WKTElement", geometry)
    point: _Point = cast("_Point", to_shape(cast_geom))
    return Coordinates(latitude=point.y, longitude=point.x)


def _gen_id() -> str:
    """Generate a stable UUID primary key string.

    Used by mappers for entities that don't carry an ``id`` in their domain
    constructor (WeatherSnapshot/RiskAssessment/Alert). The caller (repository)
    is still welcome to override ``orm.id`` explicitly if desired.
    """
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Zone
# ---------------------------------------------------------------------------


def zone_to_domain(orm: ZoneModel) -> Zone:
    from domain.entities.zone import Zone

    return Zone(
        id=orm.id,
        name=orm.name,
        coordinates=_wkb_to_coords(orm.coordinates),
        upstream_zone_id=orm.upstream_zone_id,
    )


def zone_to_orm(entity: Zone) -> ZoneModel:
    return ZoneModel(
        id=entity.id,
        name=entity.name,
        coordinates=_coords_to_wkb(entity.coordinates),
        upstream_zone_id=entity.upstream_zone_id,
    )


def zone_thresholds_to_domain(orm: ZoneThresholdsModel) -> ZoneThresholds:
    from domain.value_objects.water_level import WaterLevel
    from domain.value_objects.zone_thresholds import ZoneThresholds as DomainZT

    return DomainZT(
        water_warning_level=WaterLevel(orm.water_warning_level_cm),
        water_critical_level=WaterLevel(orm.water_critical_level_cm),
        heavy_rain_threshold_mm=orm.heavy_rain_threshold_mm,
    )


def zone_thresholds_to_orm(
    entity: ZoneThresholds,
    *,
    zone_id: str,
    id: str | None = None,
) -> ZoneThresholdsModel:
    return ZoneThresholdsModel(
        id=id or _gen_id(),
        zone_id=zone_id,
        water_warning_level_cm=entity.water_warning_level.centimetres,
        water_critical_level_cm=entity.water_critical_level.centimetres,
        heavy_rain_threshold_mm=entity.heavy_rain_threshold_mm,
    )


# ---------------------------------------------------------------------------
# ResourceCenter + InventoryItem
# ---------------------------------------------------------------------------


def resource_center_to_domain(orm: ResourceCenterModel) -> ResourceCenter:
    from domain.entities.resource_center import ResourceCenter

    return ResourceCenter(
        id=orm.id,
        name=orm.name,
        location_zone=orm.location_zone,
    )


def resource_center_to_orm(entity: ResourceCenter) -> ResourceCenterModel:
    return ResourceCenterModel(
        id=entity.id,
        name=entity.name,
        location_zone=entity.location_zone,
    )


def inventory_item_to_domain(orm: InventoryItemModel) -> InventoryItem:
    from domain.entities.inventory_item import InventoryItem

    return InventoryItem(
        id=orm.id,
        item_name=orm.item_name,
        quantity=orm.quantity,
        center_id=orm.center_id,
    )


def inventory_item_to_orm(entity: InventoryItem) -> InventoryItemModel:
    return InventoryItemModel(
        id=entity.id,
        item_name=entity.item_name,
        quantity=entity.quantity,
        center_id=entity.center_id,
    )


# ---------------------------------------------------------------------------
# Users + APIKeys
# ---------------------------------------------------------------------------


def user_to_domain(orm: UserModel) -> User:
    from domain.entities.user import User

    # Handle both enum instance and string (asyncpg might return string)
    role_value = orm.role.value if hasattr(orm.role, "value") else orm.role
    return User(
        id=orm.id,
        username=orm.username,
        role=role_value,  # DBUserRole.admin.value == "admin" or "admin"
        created_at=orm.created_at,
    )


def user_to_orm(entity: User) -> UserModel:
    return UserModel(
        id=entity.id,
        username=entity.username,
        role=DBUserRole(entity.role),
        created_at=entity.created_at,
    )


def api_key_to_domain(orm: APIKeyModel) -> APIKey:
    from domain.entities.api_key import APIKey

    return APIKey(
        id=orm.id,
        key_hash=orm.key_hash,
        owner_name=orm.owner_name,
        is_active=orm.is_active,
    )


def api_key_to_orm(entity: APIKey) -> APIKeyModel:
    return APIKeyModel(
        id=entity.id,
        key_hash=entity.key_hash,
        owner_name=entity.owner_name,
        is_active=entity.is_active,
    )


# ---------------------------------------------------------------------------
# Time-series / append-only tables
# ---------------------------------------------------------------------------


def sensor_reading_to_domain(orm: SensorReadingModel) -> SensorReading:
    from domain.entities.sensor_reading import SensorReading
    from domain.value_objects.water_level import WaterLevel

    return SensorReading(
        id=orm.id,
        zone_id=orm.zone_id,
        water_level=WaterLevel(orm.water_level_cm),
        timestamp=orm.timestamp,
        source=orm.source.value,  # "real" | "test"
    )


def sensor_reading_to_orm(entity: SensorReading) -> SensorReadingModel:
    return SensorReadingModel(
        id=entity.id,
        zone_id=entity.zone_id,
        water_level_cm=entity.water_level.centimetres,
        timestamp=entity.timestamp,
        source=DBSensorSource(entity.source),
    )


def weather_snapshot_to_domain(orm: WeatherSnapshotModel) -> WeatherSnapshot:
    from domain.entities.weather_snapshot import WeatherSnapshot
    from domain.value_objects.rainfall_window import RainfallWindow

    return WeatherSnapshot(
        zone_id=orm.zone_id,
        rainfall=RainfallWindow(
            millimetres=orm.rainfall_mm,
            duration_hours=orm.rainfall_hours,
        ),
        fetched_at=orm.fetched_at,
        ttl_seconds=int(orm.ttl_seconds),
    )


def weather_snapshot_to_orm(entity: WeatherSnapshot, *, id: str | None = None) -> WeatherSnapshotModel:
    return WeatherSnapshotModel(
        id=id or _gen_id(),
        zone_id=entity.zone_id,
        rainfall_mm=entity.rainfall.millimetres,
        rainfall_hours=entity.rainfall.duration_hours,
        fetched_at=entity.fetched_at,
        ttl_seconds=entity.ttl_seconds,
    )


def risk_assessment_to_domain(orm: RiskAssessmentModel) -> RiskAssessment:
    from domain.entities.risk_assessment import RiskAssessment as DomainRiskAssessment
    from domain.value_objects.risk_tier import RiskTier as DomainRiskTier

    return DomainRiskAssessment(
        zone_id=orm.zone_id,
        tier=_enum_name_to_domain(orm.tier, DomainRiskTier),
        probability=orm.probability,
        explanation=orm.explanation,
        computed_at=orm.computed_at,
        combined_rain_mm=orm.combined_rain_mm,
        expected_rain_mm=orm.expected_rain_mm,
        rainfall_anomaly_ratio=orm.rainfall_anomaly_ratio,
        top_contributing_features=orm.top_contributing_features,
    )


def risk_assessment_to_orm(
    entity: RiskAssessment,
    *,
    id: str | None = None,
) -> RiskAssessmentModel:
    return RiskAssessmentModel(
        id=id or _gen_id(),
        zone_id=entity.zone_id,
        tier=_domain_enum_to_db(entity.tier, DBRiskTier),
        probability=entity.probability,
        explanation=entity.explanation,
        computed_at=entity.computed_at,
        combined_rain_mm=entity.combined_rain_mm,
        expected_rain_mm=entity.expected_rain_mm,
        rainfall_anomaly_ratio=entity.rainfall_anomaly_ratio,
        top_contributing_features=entity.top_contributing_features,
    )


# ---------------------------------------------------------------------------
# Alerts, community reports, manual overrides, audit log
# ---------------------------------------------------------------------------


def alert_to_domain(orm: AlertModel) -> Alert:
    from domain.entities.alert import Alert as DomainAlert
    from domain.value_objects.risk_tier import RiskTier as DomainRiskTier

    return DomainAlert(
        zone_id=orm.zone_id,
        severity=_enum_name_to_domain(orm.severity, DomainRiskTier),
        certainty=orm.certainty,
        urgency=orm.urgency,
        headline=orm.headline,
        description=orm.description,
        sent_at=orm.sent_at,
    )


def alert_to_orm(entity: Alert, *, id: str | None = None) -> AlertModel:
    return AlertModel(
        id=id or _gen_id(),
        zone_id=entity.zone_id,
        severity=_domain_enum_to_db(entity.severity, DBRiskTier),
        certainty=entity.certainty,
        urgency=entity.urgency,
        headline=entity.headline,
        description=entity.description,
        sent_at=entity.sent_at,
    )


def community_report_to_domain(orm: CommunityReportModel) -> CommunityReport:
    from domain.entities.community_report import CommunityReport

    return CommunityReport(
        id=orm.id,
        zone_id=orm.zone_id,
        observation=orm.observation,
        status=orm.status.value,  # "Pending" | "Approved" | "Rejected"
        submitted_at=orm.submitted_at,
    )


def community_report_to_orm(entity: CommunityReport) -> CommunityReportModel:
    return CommunityReportModel(
        id=entity.id,
        zone_id=entity.zone_id,
        observation=entity.observation,
        status=DBCommunityReportStatus(entity.status),
        submitted_at=entity.submitted_at,
    )


def manual_override_to_domain(orm: ManualOverrideModel) -> ManualOverride:
    from domain.entities.manual_override import ManualOverride
    from domain.value_objects.risk_tier import RiskTier as DomainRiskTier

    return ManualOverride(
        id=orm.id,
        zone_id=orm.zone_id,
        threat_level=_enum_name_to_domain(orm.threat_level, DomainRiskTier),
        reason=orm.reason,
        admin_username=orm.admin_username,
        timestamp=orm.timestamp,
    )


def manual_override_to_orm(entity: ManualOverride) -> ManualOverrideModel:
    return ManualOverrideModel(
        id=entity.id,
        zone_id=entity.zone_id,
        threat_level=_domain_enum_to_db(entity.threat_level, DBRiskTier),
        reason=entity.reason,
        admin_username=entity.admin_username,
        timestamp=entity.timestamp,
    )


def audit_log_entry_to_domain(orm: AuditLogEntryModel) -> AuditLogEntry:
    from domain.entities.audit_log_entry import AuditLogEntry

    return AuditLogEntry(
        id=orm.id,
        actor_username=orm.actor_username,
        action=orm.action,
        target=orm.target,
        timestamp=orm.timestamp,
    )


def audit_log_entry_to_orm(entity: AuditLogEntry) -> AuditLogEntryModel:
    return AuditLogEntryModel(
        id=entity.id,
        actor_username=entity.actor_username,
        action=entity.action,
        target=entity.target,
        timestamp=entity.timestamp,
    )


# ---------------------------------------------------------------------------


def zone_terrain_features_to_dict(orm: ZoneTerrainFeaturesModel) -> dict[str, float | int]:
    """Convert a ZoneTerrainFeaturesModel ORM row → a plain feature dict.

    Keys are the 26 ML feature names; values are left as their Python-native
    types (float for terrain/rain cols, int for landcover_encoded). The predictor
    reorders via the canonical ``feature_columns`` list, so dict key order
    doesn't matter here.
    """
    result: dict[str, float | int] = {}
    for field in _ZONE_TERRAIN_FEATURE_FIELDS:
        result[field] = getattr(orm, field)
    return result


def zone_terrain_features_to_orm(
    features: dict[str, float | int],
    *,
    zone_id: str,
    id: str | None = None,
) -> ZoneTerrainFeaturesModel:
    """Build a ZoneTerrainFeaturesModel from a feature dict + zone_id.

    Validates that all 26 required keys are present before instantiating the
    ORM model — a KeyError with the missing key name is raised if any field
    is absent.
    """
    missing = [k for k in _ZONE_TERRAIN_FEATURE_FIELDS if k not in features]
    if missing:
        raise KeyError(
            f"Missing terrain feature keys: {missing}. "
            f"Expected all of {list(_ZONE_TERRAIN_FEATURE_FIELDS)}."
        )
    kwargs: dict[str, object] = {"zone_id": zone_id}
    for field in _ZONE_TERRAIN_FEATURE_FIELDS:
        kwargs[field] = features[field]
    return ZoneTerrainFeaturesModel(id=id or _gen_id(), **kwargs)


__all__ = [
    "alert_to_domain",
    "alert_to_orm",
    "api_key_to_domain",
    "api_key_to_orm",
    "audit_log_entry_to_domain",
    "audit_log_entry_to_orm",
    "community_report_to_domain",
    "community_report_to_orm",
    "inventory_item_to_domain",
    "inventory_item_to_orm",
    "manual_override_to_domain",
    "manual_override_to_orm",
    "resource_center_to_domain",
    "resource_center_to_orm",
    "risk_assessment_to_domain",
    "risk_assessment_to_orm",
    "sensor_reading_to_domain",
    "sensor_reading_to_orm",
    "user_to_domain",
    "user_to_orm",
    "weather_snapshot_to_domain",
    "weather_snapshot_to_orm",
    "zone_terrain_features_to_dict",
    "zone_terrain_features_to_orm",
    "zone_thresholds_to_domain",
    "zone_thresholds_to_orm",
    "zone_to_domain",
    "zone_to_orm",
]
