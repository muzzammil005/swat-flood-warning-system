from __future__ import annotations

from dataclasses import dataclass

from domain.exceptions import DomainError


@dataclass
class APIKey:
    """A long-lived credential for non-interactive clients (field-logger IoT
    boxes pushing SensorReading over HTTP, batch job scrapers, etc.).

    Invariant: we *only* store ``key_hash`` — the raw key is shown to the
    caller exactly once on creation, then discarded. If we ever catch a raw
    string being stored here, the whole credential rotation story breaks.
    """

    id: str
    key_hash: str
    owner_name: str
    is_active: bool

    def __post_init__(self) -> None:
        if not self.key_hash:
            raise DomainError(
                "APIKey.key_hash must be non-empty (store a hash, never the raw key)"
            )
        if not self.owner_name:
            raise DomainError("APIKey.owner_name must be non-empty for audit purposes")
