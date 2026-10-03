"""Repository ports — abstract interfaces for persistent aggregate storage.

Every port here is an :class:`abc.ABC` with :class:`abc.abstractmethod` bodies (``...``
only). Implementations live in :mod:`infrastructure.db.repositories` and use the
SQLAlchemy async session from Prompt 3; the application use cases (Stage 3) depend on
these interfaces, never on the concrete classes — that's what lets us swap storage
backends (e.g. SQLite → PostGIS, or a test fake) without touching application logic.

Append-only repositories (SensorReading, WeatherSnapshot, RiskAssessment, Alert,
AuditLog) intentionally expose *no* ``update`` method; the only way to get a new
version of a historical fact is to add a new row with a newer timestamp. Mutable
repositories expose ``update`` only for fields that are genuinely live state
(CommunityReport status, InventoryItem quantity, User profile, etc.).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

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


# ---------------------------------------------------------------------------
# Append-only repositories — no update() method.
# ---------------------------------------------------------------------------


class SensorReadingRepository(ABC):
    """Persistent store for water-level observations.

    Sensor readings are *measurements*: once a gauge produces a reading at a given
    timestamp, that value is a historical fact and can never be revised. Callers
    that want to "correct" a bad reading should add a new row with a note rather
    than mutating the original — this is what makes the table auditable.
    """

    @abstractmethod
    async def get_by_id(self, reading_id: str, /) -> SensorReading | None: ...

    @abstractmethod
    async def list_for_zone(
        self, zone_id: str, /, *, limit: int = 100
    ) -> list[SensorReading]:
        """Return the most recent ``limit`` readings for ``zone_id`` (newest first)."""
        ...

    @abstractmethod
    async def add(self, reading: SensorReading, /) -> SensorReading: ...


class WeatherSnapshotRepository(ABC):
    """TTL-bounded weather forecasts from a provider.

    Snapshots are append-only because a *fetched* forecast never changes — a fresh
    call to the provider produces a brand-new snapshot with a newer ``fetched_at``.
    The cache adapter (Prompt 6) sits in front of the provider; this repository
    is the longer-lived DB record for provenance.
    """

    @abstractmethod
    async def get_by_id(self, snapshot_id: str, /) -> WeatherSnapshot | None: ...

    @abstractmethod
    async def latest_for_zone(self, zone_id: str, /) -> WeatherSnapshot | None: ...

    @abstractmethod
    async def list_for_zone_in_window(
        self, zone_id: str, /, *, start_time: datetime
    ) -> list[WeatherSnapshot]:
        ...

    @abstractmethod
    async def add(self, snapshot: WeatherSnapshot, /) -> WeatherSnapshot: ...


class RiskAssessmentRepository(ABC):
    """Append-only assessments produced each cycle by RiskEngine + EscalationEngine.

    Every cycle produces a brand-new row — never UPDATE an existing assessment.
    Stage 3's ``AssessZoneRisk`` use case will call :meth:`add` exactly once per
    zone per cycle. The SHAP explainability panel in the web UI (Stage 6) reads
    history from here.
    """

    @abstractmethod
    async def get_by_id(self, assessment_id: str, /) -> RiskAssessment | None: ...

    @abstractmethod
    async def latest_for_zone(self, zone_id: str, /) -> RiskAssessment | None: ...

    @abstractmethod
    async def history_for_zone(
        self, zone_id: str, /, *, limit: int = 50
    ) -> list[RiskAssessment]:
        ...

    @abstractmethod
    async def list_for_zone_in_window(
        self, zone_id: str, /, *, start_time: datetime
    ) -> list[RiskAssessment]:
        ...

    @abstractmethod
    async def add(self, assessment: RiskAssessment, /) -> RiskAssessment: ...


class AlertRepository(ABC):
    """CAP-inspired public alerts.

    Alerts are append-only because a *sent* alert never changes; a correction or
    cancellation is a new Alert row with a newer ``sent_at`` and a reference in
    its description. We don't model the reference relation in the domain entity
    yet but keeping this append-only leaves room for it later without a rewrite.
    """

    @abstractmethod
    async def get_by_id(self, alert_id: str, /) -> Alert | None: ...

    @abstractmethod
    async def list_active(
        self, *, limit: int = 50
    ) -> list[Alert]:
        """Return the most recent alerts — Stage 3 filtering logic decides active."""
        ...

    @abstractmethod
    async def add(self, alert: Alert, /) -> Alert: ...


class AuditLogRepository(ABC):
    """Append-only trail of every human- or system-driven state change.

    This repository is write-mostly-read-rarely; Stage 3's ``ModerateReport`` and
    ``IssueManualOverride`` use cases will append a row after every successful
    action. Intentionally no list_by_actor filters here yet — add them when a
    concrete use case needs the audit trail read back.
    """

    @abstractmethod
    async def get_by_id(self, entry_id: str, /) -> AuditLogEntry | None: ...

    @abstractmethod
    async def add(self, entry: AuditLogEntry, /) -> AuditLogEntry: ...


# ---------------------------------------------------------------------------
# Mutable repositories — expose update() in addition to get/list/add.
# ---------------------------------------------------------------------------


class ZoneRepository(ABC):
    """River-basin sub-catchments + upstream graph edges.

    Mutable because a zone's name / coordinates / upstream neighbour can be
    edited by an admin when the calibration team revises the river network.

    Thresholds are *not* part of the Zone aggregate — they live in a separate
    :class:`ZoneThresholdsRepository` with a ``zone_id UNIQUE`` invariant.
    RiskEngine callers load a Zone and its ZoneThresholds as two distinct
    parameters from two distinct repositories.
    """

    @abstractmethod
    async def get_by_id(self, zone_id: str, /) -> Zone | None: ...

    @abstractmethod
    async def get_by_name(self, name: str, /) -> Zone | None: ...

    @abstractmethod
    async def find_nearest(self, latitude: float, longitude: float, /) -> Zone | None: ...

    @abstractmethod
    async def list_all(self) -> list[Zone]: ...

    @abstractmethod
    async def add(self, zone: Zone, /) -> Zone: ...

    @abstractmethod
    async def update(self, zone: Zone, /) -> Zone: ...


class ZoneThresholdsRepository(ABC):
    """Per-zone calibration knobs for the risk engine.

    Exactly one row per ``zone_id`` is enforced by a DB ``UNIQUE`` constraint.
    The surface is deliberately narrower than other mutable repos: callers
    don't choose between add vs update — :meth:`upsert` handles both cases
    (INSERT on first write, UPDATE on re-calibration) so the caller never
    needs to branch on "does this zone already have thresholds?".

    The invariant ``water_critical_level > water_warning_level`` is enforced
    in the domain :class:`ZoneThresholds` ``__post_init__`` before the repo
    ever sees it, so the implementation here doesn't need to re-check.
    """

    @abstractmethod
    async def get_by_zone_id(self, zone_id: str, /) -> ZoneThresholds | None: ...

    @abstractmethod
    async def upsert(
        self, zone_id: str, thresholds: ZoneThresholds, /
    ) -> ZoneThresholds:
        """Insert thresholds for ``zone_id`` or overwrite any existing row.

        Returns the persisted (or overwritten) thresholds. The returned value
        is functionally identical to the input but is useful for tests that
        want to confirm a round-trip.
        """
        ...


class CommunityReportRepository(ABC):
    """Civilian ground-truth reports; status transitions are the only mutation.

    A report enters as ``Pending`` and a responder moves it to ``Approved`` or
    ``Rejected`` (Stage 3 :class:`ModerateCommunityReport`). The observation text
    itself is frozen on submission — if the user made a typo, the moderation
    comment goes into the audit log, not an UPDATE here.
    """

    @abstractmethod
    async def get_by_id(self, report_id: str, /) -> CommunityReport | None: ...

    @abstractmethod
    async def list_pending(self, *, limit: int = 50) -> list[CommunityReport]: ...

    @abstractmethod
    async def list_for_zone(
        self, zone_id: str, /, *, limit: int = 50
    ) -> list[CommunityReport]:
        ...

    @abstractmethod
    async def list_with_filters(
        self, *, status: str | None = None, zone_id: str | None = None, limit: int = 100
    ) -> list[CommunityReport]:
        ...

    @abstractmethod
    async def add(self, report: CommunityReport, /) -> CommunityReport: ...

    @abstractmethod
    async def update_status(
        self, report: CommunityReport, /, *, new_status: str
    ) -> CommunityReport:
        """Update only the status field (and never the observation text)."""
        ...


class ManualOverrideRepository(ABC):
    """Admin-signed forced risk tiers.

    Mutable because a manual override can be *revoked* (set an expires-at flag or
    soft-delete pattern depending on Stage 3 design). Keeping update() here
    rather than forcing a new append-only row is fine because overrides are
    operator actions, not historical measurements — the corresponding audit log
    entry is the append-only record of who issued/revoked it.
    """

    @abstractmethod
    async def get_by_id(self, override_id: str, /) -> ManualOverride | None: ...

    @abstractmethod
    async def active_for_zone(self, zone_id: str, /) -> ManualOverride | None: ...

    @abstractmethod
    async def add(self, override: ManualOverride, /) -> ManualOverride: ...

    @abstractmethod
    async def update(self, override: ManualOverride, /) -> ManualOverride: ...


class ResourceCenterRepository(ABC):
    """Depot/staging-area locations for response inventory.

    Mutable admin catalog — name or owning zone changes when a centre is renamed
    or relocated. InventoryItem rows hang off centre_id as a foreign key.
    """

    @abstractmethod
    async def get_by_id(self, center_id: str, /) -> ResourceCenter | None: ...

    @abstractmethod
    async def list_all(self) -> list[ResourceCenter]: ...

    @abstractmethod
    async def list_for_zone(self, zone_id: str, /) -> list[ResourceCenter]: ...

    @abstractmethod
    async def add(self, center: ResourceCenter, /) -> ResourceCenter: ...

    @abstractmethod
    async def update(self, center: ResourceCenter, /) -> ResourceCenter: ...


class InventoryItemRepository(ABC):
    """Single SKU inside a ResourceCenter; quantity is the mutable field.

    Stage 3's :class:`AllocateResources` use case will atomically decrement
    ``quantity`` here. All other fields (name, owning centre) are edited via
    the blanket update() admin path.
    """

    @abstractmethod
    async def get_by_id(self, item_id: str, /) -> InventoryItem | None: ...

    @abstractmethod
    async def list_for_center(self, center_id: str, /) -> list[InventoryItem]: ...

    @abstractmethod
    async def add(self, item: InventoryItem, /) -> InventoryItem: ...

    @abstractmethod
    async def update(self, item: InventoryItem, /) -> InventoryItem: ...


class UserRepository(ABC):
    """Operator accounts (admin / responder).

    Mutable profile (password hash, role on promotion/demotion, etc.). Password
    hashing itself lives in :class:`PasswordHasherPort` — this repository only
    stores the resulting hash string on the User entity.
    """

    @abstractmethod
    async def get_by_id(self, user_id: str, /) -> User | None: ...

    @abstractmethod
    async def get_by_username(self, username: str, /) -> User | None: ...

    @abstractmethod
    async def list_all(self) -> list[User]: ...

    @abstractmethod
    async def add(self, user: User, /) -> User: ...

    @abstractmethod
    async def update(self, user: User, /) -> User: ...


class APIKeyRepository(ABC):
    """Revocable M2M credentials.

    Key *hashes* only — raw keys are never written to storage. ``is_active``
    toggle via update() is the revocation path.
    """

    @abstractmethod
    async def get_by_id(self, key_id: str, /) -> APIKey | None: ...

    @abstractmethod
    async def get_by_hash(self, key_hash: str, /) -> APIKey | None: ...

    @abstractmethod
    async def list_active(self) -> list[APIKey]: ...

    @abstractmethod
    async def add(self, api_key: APIKey, /) -> APIKey: ...

    @abstractmethod
    async def update(self, api_key: APIKey, /) -> APIKey: ...


class ZoneTerrainFeaturesRepository(ABC):
    """Static per-zone ML feature vector — 22 static columns.

    One row per zone, loaded once from the CSV. These are *ground-truth
    geographic features* — never mutated at runtime (distinct from
    ZoneThresholds, which are admin-calibration knobs).

    The repository returns a plain ``dict`` keyed by feature name because the
    ML predictor in :mod:`infrastructure.ml.predictor` consumes a dict directly
    — no domain value-object wrapping is needed for this infrastructure-only
    aggregate.
    """

    @abstractmethod
    async def get_by_zone_id(self, zone_id: str, /) -> dict[str, float | int] | None:
        """Return the 22 static feature dict for ``zone_id``, or None if no row exists."""
        ...

    @abstractmethod
    async def upsert(
        self, zone_id: str, features: dict[str, float | int], /
    ) -> dict[str, float | int]:
        """Insert terrain features for ``zone_id`` or overwrite any existing row.

        Returns the persisted features (same dict shape as :meth:`get_by_zone_id`).
        """
        ...
