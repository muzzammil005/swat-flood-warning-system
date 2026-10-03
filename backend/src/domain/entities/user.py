from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from domain.exceptions import DomainError

if TYPE_CHECKING:
    from datetime import datetime


@dataclass
class User:
    """An operator account (admin or field responder) that can log in to the
    web/mobile portal and trigger auditable actions.

    We intentionally keep the profile minimal here — "real" user fields
    (full name, contact number) are Stage 2 concerns when we build the
    application-layer auth port. The domain layer only cares about the two
    role distinctions that alter business rules: admins can issue
    ManualOverrides, responders can moderate CommunityReports.
    """

    id: str
    username: str
    role: Literal["admin", "responder"]
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.username:
            raise DomainError("User.username must be non-empty")
        if self.role not in {"admin", "responder"}:
            raise DomainError(
                f"User.role must be 'admin' or 'responder', got {self.role!r}"
            )
