from __future__ import annotations

from dataclasses import dataclass

from domain.exceptions import DomainError


@dataclass
class ResourceCenter:
    """A depot where flood-response inventory is stored.

    Linked to a zone via ``location_zone`` (a zone_id string, not a foreign
    object reference — the application layer resolves the join) so the
    ``AllocateResources`` use case (Stage 3) can pick the closest centre to a
    zone whose risk just spiked.
    """

    id: str
    name: str
    location_zone: str

    def __post_init__(self) -> None:
        if not self.name:
            raise DomainError("ResourceCenter.name must be non-empty")
        if not self.location_zone:
            raise DomainError("ResourceCenter.location_zone must reference a zone id")
