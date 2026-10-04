"""SQLAlchemy 2.0 async ORM models mirroring the domain entity aggregate.

Design rules enforced here (viva-readiness):

1. **ORM never leaks into the domain layer.** All conversion between ORM rows
   and domain classes happens in :mod:`infrastructure.db.mappers` — a repository
   (Prompt 4) fetches a row from this module, pipes it through
   ``mappers.to_domain()``, and hands the domain entity to the application
   layer. The reverse direction uses ``mappers.to_orm()`` before writing.

2. **Value-object primitives on the ORM side.** WaterLevel (float cm),
   RiskTier (native Postgres ENUM), RainfallWindow (two float cols: mm + h),
   and Coordinates (GeoAlchemy2 Geography(Point, 4326)) are *not* stored as
   their domain types — the ORM deals with primitive DB types and the mapper
   wraps them back into domain value objects. This keeps PostgreSQL happy
   (GeoAlchemy2 speaks raw WKB for points) and keeps the domain pure.

3. **Append-only tables get no ``updated_at``.** SensorReading,
   RiskAssessment, Alert, WeatherSnapshot, AuditLogEntry are INSERT-only and
   only ever have a single timestamp column (the event time). Mutable tables
   (Zone, InventoryItem, User, etc.) don't bother with updated_at right now
   because Stage 3 doesn't expose concurrency control yet — add it as an
   optimistic-lock column when Stage 5 hardening starts.

4. **PostGIS Geography(Point, 4326) for Zone.coordinates.** Geometry columns
   can use GIST spatial indexes (§5 of the architecture doc) and PostGIS's
   ``ST_DWithin`` / ``ST_Distance`` operators instead of a linear O(n)
   haversine loop when we later add "nearest-zone" endpoints.

5. **Native Postgres ENUMs for RiskTier + status columns.** Text would work
   but native ENUMs give us built-in validation, compressed storage, and a
   signal to any future DBAs that this column's universe is constrained.

6. **Composite ``(zone_id, timestamp)`` indexes on time-series tables.** All
   three of SensorReading / WeatherSnapshot / RiskAssessment are queried by
   "give me the most recent N rows for zone Z" — the exact shape a B-tree on
   ``(zone_id, <time> DESC)`` is built for.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum

from geoalchemy2 import Geography
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# ---------------------------------------------------------------------------
# Native Postgres ENUMs — match the domain RiskTier (IntEnum) ordering so
# ORDER BY tier works directly in SQL. We use a separate native enum per
# status column so future migrations (e.g. adding a new status) are local to
# that enum.
# ---------------------------------------------------------------------------


class DBRiskTier(PyEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class DBSensorSource(PyEnum):
    real = "real"
    test = "test"


class DBCommunityReportStatus(PyEnum):
    Pending = "Pending"
    Approved = "Approved"
    Rejected = "Rejected"


class DBUserRole(PyEnum):
    admin = "admin"
    responder = "responder"


class Base(DeclarativeBase):
    """Root declarative base. Alembic ``env.py`` imports ``Base.metadata``."""

    type_annotation_map = {
        datetime: DateTime(timezone=True),
    }


# ---------------------------------------------------------------------------
# Zone — river-basin sub-catchment (Kalam, Bahrain, Madyan, Mingora, ...)
# Self-referential upstream_zone_id for the directed escalation graph.
# ---------------------------------------------------------------------------


class ZoneModel(Base):
    __tablename__ = "zones"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    # Geography(Point, 4326): WGS84 lon/lat order (x=lon, y=lat).
    coordinates: Mapped[object] = mapped_column(
        Geography(geometry_type="POINT", srid=4326),
        nullable=False,
    )
    upstream_zone_id: Mapped[str | None] = mapped_column(
        ForeignKey("zones.id", ondelete="SET NULL"),
        nullable=True,
    )


class ZoneThresholdsModel(Base):
    """Per-zone calibration knobs consumed by :class:`RiskEngine`.

    Deliberately a *separate* table from zones (not embedded columns) because
    thresholds are a distinct lifecycle: admins re-calibrate thresholds
    independently of renaming a zone or editing its river-graph edges, and a
    separate aggregate with ``zone_id UNIQUE`` gives us exactly-one-row-per-zone
    semantics enforced by the database rather than by application convention.
    """

    __tablename__ = "zone_thresholds"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    zone_id: Mapped[str] = mapped_column(
        ForeignKey("zones.id", ondelete="CASCADE"),
        nullable=False,
    )
    # WaterLevel → primitive float cm columns (VO wrapping done in mappers).
    water_warning_level_cm: Mapped[float] = mapped_column(Float, nullable=False)
    water_critical_level_cm: Mapped[float] = mapped_column(Float, nullable=False)
    heavy_rain_threshold_mm: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint("zone_id", name="uq_zone_thresholds_zone_id"),
    )


class ZoneTerrainFeaturesModel(Base):
    """Static per-zone ML feature vector — 22 static columns.

    Architecture decision (viva-readiness):
    Kept distinct from ``ZoneThresholds`` even though both are one-row-per-zone.
    ZoneThresholds are *calibration knobs* an admin re-tunes during operations;
    ZoneTerrainFeatures are *ground-truth geographic features* loaded once from
    the CSV and never edited at runtime. Two separate aggregates = two
    separate lifecycles = no accidental UPDATE of terrain features when an
    admin tweaks a threshold.
    """

    __tablename__ = "zone_terrain_features"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    zone_id: Mapped[str] = mapped_column(
        ForeignKey("zones.id", ondelete="CASCADE"),
        nullable=False,
    )

    elevation: Mapped[float] = mapped_column(Float, nullable=False)
    slope: Mapped[float] = mapped_column(Float, nullable=False)
    stream_proximity: Mapped[float] = mapped_column(Float, nullable=False)
    drainage_density: Mapped[float] = mapped_column(Float, nullable=False)
    upstream_area: Mapped[float] = mapped_column(Float, nullable=False)
    hand: Mapped[float] = mapped_column(Float, nullable=False)
    landcover_encoded: Mapped[int] = mapped_column(Integer, nullable=False)
    ndvi: Mapped[float] = mapped_column(Float, nullable=False)
    rain_jan: Mapped[float] = mapped_column(Float, nullable=False)
    rain_feb: Mapped[float] = mapped_column(Float, nullable=False)
    rain_mar: Mapped[float] = mapped_column(Float, nullable=False)
    rain_apr: Mapped[float] = mapped_column(Float, nullable=False)
    rain_may: Mapped[float] = mapped_column(Float, nullable=False)
    rain_jun: Mapped[float] = mapped_column(Float, nullable=False)
    rain_jul: Mapped[float] = mapped_column(Float, nullable=False)
    rain_aug: Mapped[float] = mapped_column(Float, nullable=False)
    rain_sep: Mapped[float] = mapped_column(Float, nullable=False)
    rain_oct: Mapped[float] = mapped_column(Float, nullable=False)
    rain_nov: Mapped[float] = mapped_column(Float, nullable=False)
    rain_dec: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint("zone_id", name="uq_zone_terrain_features_zone_id"),
    )


# ---------------------------------------------------------------------------
# ResourceCenter + InventoryItem
# ---------------------------------------------------------------------------


class ResourceCenterModel(Base):
    __tablename__ = "resource_centers"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location_zone: Mapped[str] = mapped_column(
        ForeignKey("zones.id", ondelete="RESTRICT"),
        nullable=False,
    )


class InventoryItemModel(Base):
    __tablename__ = "inventory_items"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    center_id: Mapped[str] = mapped_column(
        ForeignKey("resource_centers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


# ---------------------------------------------------------------------------
# Users + API keys (auth)
# ---------------------------------------------------------------------------


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    role: Mapped[DBUserRole] = mapped_column(
        SAEnum(DBUserRole, name="user_role", native_enum=True, create_constraint=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    # Optional: password_hash column — Stage 3's RegisterUser writes here.
    # Kept nullable so the domain entity can be round-tripped even if the
    # caller hasn't hashed a password yet (e.g. admin-created responder).
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)


class APIKeyModel(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    owner_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


# ---------------------------------------------------------------------------
# Append-only time-series tables
# ---------------------------------------------------------------------------


class SensorReadingModel(Base):
    __tablename__ = "sensor_readings"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    zone_id: Mapped[str] = mapped_column(
        ForeignKey("zones.id", ondelete="CASCADE"),
        nullable=False,
    )
    # WaterLevel → primitive float cm column.
    water_level_cm: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(nullable=False)
    source: Mapped[DBSensorSource] = mapped_column(
        SAEnum(
            DBSensorSource,
            name="sensor_source",
            native_enum=True,
            create_constraint=True,
        ),
        nullable=False,
    )

    __table_args__ = (
        Index(
            "ix_sensor_readings_zone_timestamp",
            "zone_id",
            "timestamp",
            postgresql_using="btree",
        ),
    )


class WeatherSnapshotModel(Base):
    __tablename__ = "weather_snapshots"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    zone_id: Mapped[str] = mapped_column(
        ForeignKey("zones.id", ondelete="CASCADE"),
        nullable=False,
    )
    # RainfallWindow → two primitive cols.
    rainfall_mm: Mapped[float] = mapped_column(Float, nullable=False)
    rainfall_hours: Mapped[float] = mapped_column(Float, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(nullable=False)
    ttl_seconds: Mapped[int] = mapped_column(BigInteger, nullable=False)

    __table_args__ = (
        Index(
            "ix_weather_snapshots_zone_fetched",
            "zone_id",
            "fetched_at",
            postgresql_using="btree",
        ),
    )


class RiskAssessmentModel(Base):
    __tablename__ = "risk_assessments"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    zone_id: Mapped[str] = mapped_column(
        ForeignKey("zones.id", ondelete="CASCADE"),
        nullable=False,
    )
    tier: Mapped[DBRiskTier] = mapped_column(
        SAEnum(
            DBRiskTier,
            name="risk_tier",
            native_enum=True,
            create_constraint=True,
        ),
        nullable=False,
    )
    probability: Mapped[float] = mapped_column(Float, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(nullable=False)
    combined_rain_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_rain_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    rainfall_anomaly_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    top_contributing_features: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index(
            "ix_risk_assessments_zone_computed",
            "zone_id",
            "computed_at",
            postgresql_using="btree",
        ),
    )


# ---------------------------------------------------------------------------
# CAP-inspired alerts, Community reports, Manual overrides, Audit log
# ---------------------------------------------------------------------------


class AlertModel(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    zone_id: Mapped[str] = mapped_column(
        ForeignKey("zones.id", ondelete="CASCADE"),
        nullable=False,
    )
    severity: Mapped[DBRiskTier] = mapped_column(
        SAEnum(DBRiskTier, name="alert_severity", native_enum=True, create_constraint=True),
        nullable=False,
    )
    certainty: Mapped[str] = mapped_column(String(50), nullable=False)
    urgency: Mapped[str] = mapped_column(String(50), nullable=False)
    headline: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(nullable=False)


class CommunityReportModel(Base):
    __tablename__ = "community_reports"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    zone_id: Mapped[str] = mapped_column(
        ForeignKey("zones.id", ondelete="CASCADE"),
        nullable=False,
    )
    observation: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[DBCommunityReportStatus] = mapped_column(
        SAEnum(
            DBCommunityReportStatus,
            name="community_report_status",
            native_enum=True,
            create_constraint=True,
        ),
        nullable=False,
    )
    submitted_at: Mapped[datetime] = mapped_column(nullable=False)


class ManualOverrideModel(Base):
    __tablename__ = "manual_overrides"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    zone_id: Mapped[str] = mapped_column(
        ForeignKey("zones.id", ondelete="CASCADE"),
        nullable=False,
    )
    threat_level: Mapped[DBRiskTier] = mapped_column(
        SAEnum(
            DBRiskTier,
            name="override_threat_level",
            native_enum=True,
            create_constraint=True,
        ),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    admin_username: Mapped[str] = mapped_column(String(255), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(nullable=False)


class AuditLogEntryModel(Base):
    __tablename__ = "audit_log_entries"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    actor_username: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    target: Mapped[str] = mapped_column(String(255), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(nullable=False)

    __table_args__ = (
        Index(
            "ix_audit_log_entries_actor_timestamp",
            "actor_username",
            "timestamp",
            postgresql_using="btree",
        ),
    )
