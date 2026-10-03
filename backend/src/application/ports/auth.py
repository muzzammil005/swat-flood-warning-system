"""Authentication and credential ports.

Split into two deliberately narrow interfaces:

* :class:`PasswordHasherPort` — the *only* place raw passwords enter or leave
  the system. Implementations use a slow memory-hard KDF (argon2id in Prompt 7)
  and intentionally return opaque strings (never raw hashes/params).
* :class:`TokenPort` — JWT mint + verify. Access tokens are short-lived,
  refresh tokens are long-lived; Stage 4 HTTP layer uses these for the
  login/refresh flow.

Keeping them behind ports means unit tests for Stage 3's :class:`RegisterUser`
/ :class:`LoginUser` use cases can inject a deterministic no-op hasher and a
"verified=always" token service without touching argon2 or pyjwt at all.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain.entities.user import User


class PasswordHasherPort(ABC):
    """Hash and verify credentials via a memory-hard KDF."""

    @abstractmethod
    def hash(self, raw: str, /) -> str: ...

    @abstractmethod
    def verify(self, raw: str, hashed: str, /) -> bool: ...


class TokenPort(ABC):
    """Mint and validate JWT-style access/refresh tokens."""

    @abstractmethod
    def issue_access_token(self, user: User, /) -> str: ...

    @abstractmethod
    def issue_refresh_token(self, user: User, /) -> str: ...

    @abstractmethod
    def verify_token(self, token: str, /) -> dict[str, object]:
        """Return decoded claims on success, raise a clear application
        exception on invalid/expired/malformed tokens.
        """
        ...
