"""Repository implementations package — re-exports every Impl class.

From the application/interface layers, import the concrete classes from here
so you don't need to know the internal module layout:

    from infrastructure.db.repositories import (
        SensorReadingRepositoryImpl,
        ZoneRepositoryImpl,
        ...,
    )

The corresponding port ABCs are in :mod:`application.ports.repositories`; the
application layer should always depend on the ABC, never on the Impl class
directly — these concrete classes are only visible at the composition root
(FastAPI dependency injection, test fixtures).
"""

from infrastructure.db.repositories.repositories import (
    AlertRepositoryImpl,
    APIKeyRepositoryImpl,
    AuditLogRepositoryImpl,
    CommunityReportRepositoryImpl,
    InventoryItemRepositoryImpl,
    ManualOverrideRepositoryImpl,
    ResourceCenterRepositoryImpl,
    RiskAssessmentRepositoryImpl,
    SensorReadingRepositoryImpl,
    UserRepositoryImpl,
    WeatherSnapshotRepositoryImpl,
    ZoneRepositoryImpl,
    ZoneTerrainFeaturesRepositoryImpl,
    ZoneThresholdsRepositoryImpl,
)

__all__ = [
    "AlertRepositoryImpl",
    "APIKeyRepositoryImpl",
    "AuditLogRepositoryImpl",
    "CommunityReportRepositoryImpl",
    "InventoryItemRepositoryImpl",
    "ManualOverrideRepositoryImpl",
    "ResourceCenterRepositoryImpl",
    "RiskAssessmentRepositoryImpl",
    "SensorReadingRepositoryImpl",
    "UserRepositoryImpl",
    "WeatherSnapshotRepositoryImpl",
    "ZoneRepositoryImpl",
    "ZoneTerrainFeaturesRepositoryImpl",
    "ZoneThresholdsRepositoryImpl",
]
