class DomainError(Exception):
    """Base class for all domain-layer invariant violations.

    Domain code never raises raw :class:`ValueError` or :class:`RuntimeError`;
    anything that represents a violation of a domain rule is a subclass of
    :class:`DomainError`. This lets the application/interface layers distinguish
    "user/data did something wrong" from "the framework broke".
    """


class InvalidWaterLevel(DomainError):
    """Raised when a :class:`WaterLevel` is constructed with a negative value."""


class InvalidCoordinates(DomainError):
    """Raised when latitude/longitude fall outside their valid ranges."""


class InvalidRainfallWindow(DomainError):
    """Raised when a :class:`RainfallWindow` has negative millimetres or hours."""


class InvalidRiskAssessment(DomainError):
    """Raised when a :class:`RiskAssessment` breaks an invariant (e.g. probability out of range)."""


class InvalidThresholds(DomainError):
    """Raised when :class:`ZoneThresholds` fails its ordering invariant."""


class InvalidInventoryQuantity(DomainError):
    """Raised when an :class:`InventoryItem` is given a negative quantity."""


class CycleInUpstreamGraph(DomainError):
    """Raised by :class:`EscalationEngine` when the zone upstream graph has a cycle."""
