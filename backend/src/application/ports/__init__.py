"""Application ports package — dependency-inversion boundary.

Ports are abstract interfaces (:pep:`3119` ABCs) that define *what* the
application layer needs from the outside world. Concrete implementations
(repositories, weather, cache, notifications, auth) live in the infrastructure
layer and are wired in during Stage 3 use-case construction.

File→Interface map:

* :mod:`application.ports.repositories` — 13 repository ports (Zone, ZoneThresholds,
  SensorReading, WeatherSnapshot, RiskAssessment, Alert, CommunityReport,
  ManualOverride, ResourceCenter, InventoryItem, User, APIKey, AuditLog).
* :mod:`application.ports.weather` — :class:`WeatherProvider`
* :mod:`application.ports.cache` — :class:`CachePort`
* :mod:`application.ports.notifications` — :class:`NotificationPort`
* :mod:`application.ports.auth` — :class:`PasswordHasherPort`, :class:`TokenPort`
"""

from application.ports.auth import PasswordHasherPort, TokenPort
from application.ports.cache import CachePort
from application.ports.notifications import NotificationPort
from application.ports.repositories import (
    AlertRepository,
    APIKeyRepository,
    AuditLogRepository,
    CommunityReportRepository,
    InventoryItemRepository,
    ManualOverrideRepository,
    ResourceCenterRepository,
    RiskAssessmentRepository,
    SensorReadingRepository,
    UserRepository,
    WeatherSnapshotRepository,
    ZoneRepository,
    ZoneTerrainFeaturesRepository,
    ZoneThresholdsRepository,
)
from application.ports.weather import WeatherProvider

__all__ = [
    "APIKeyRepository",
    "AlertRepository",
    "AuditLogRepository",
    "CachePort",
    "CommunityReportRepository",
    "InventoryItemRepository",
    "ManualOverrideRepository",
    "NotificationPort",
    "PasswordHasherPort",
    "ResourceCenterRepository",
    "RiskAssessmentRepository",
    "SensorReadingRepository",
    "TokenPort",
    "UserRepository",
    "WeatherProvider",
    "WeatherSnapshotRepository",
    "ZoneRepository",
    "ZoneTerrainFeaturesRepository",
    "ZoneThresholdsRepository",
]
