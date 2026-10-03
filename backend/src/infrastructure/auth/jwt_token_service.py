"""JWT token adapter for the TokenPort.

Uses python‑jose (jose.jwt) to mint and verify signed JWTs. The service
distinguishes between short‑lived access tokens (minutes) and long‑lived
refresh tokens (days), both signed with the same HMAC‑SHA256 secret.

Token payload includes the minimal claims needed by Stage 4's HTTP layer:
user id, username, role, and standard JWT fields (iss, sub, exp, iat, jti).
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from jose import JWTError, jwt
from jose.constants import ALGORITHMS

from application.ports.auth import TokenPort
from domain.exceptions.base import DomainError

if TYPE_CHECKING:
    from domain.entities.user import User


class JWTTokenService(TokenPort):
    """JWT‑based token service for access and refresh tokens."""

    def __init__(
        self,
        *,
        secret_key: str,
        issuer: str = "swat-flood-backend",
        access_token_lifetime_minutes: int = 15,
        refresh_token_lifetime_days: int = 7,
    ) -> None:
        """
        Args:
            secret_key: HMAC‑SHA256 signing secret (keep secure!)
            issuer: "iss" claim value (identifies this service)
            access_token_lifetime_minutes: How long access tokens remain valid
            refresh_token_lifetime_days: How long refresh tokens remain valid
        """
        if not secret_key:
            raise ValueError("JWTTokenService requires a non‑empty secret_key")
        if len(secret_key) < 32:
            raise ValueError(
                "JWT secret_key should be at least 32 bytes for HMAC‑SHA256"
            )

        self._secret_key = secret_key
        self._issuer = issuer
        self._access_lifetime = timedelta(minutes=access_token_lifetime_minutes)
        self._refresh_lifetime = timedelta(days=refresh_token_lifetime_days)

    def issue_access_token(self, user: User, /) -> str:
        """Mint a short‑lived JWT access token."""
        return self._create_token(
            user,
            token_type="access",
            lifetime=self._access_lifetime,
        )

    def issue_refresh_token(self, user: User, /) -> str:
        """Mint a long‑lived JWT refresh token."""
        return self._create_token(
            user,
            token_type="refresh",
            lifetime=self._refresh_lifetime,
        )

    def verify_token(self, token: str, /) -> dict[str, object]:
        """Return decoded claims on success, raise DomainError on invalid token."""
        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[ALGORITHMS.HS256],
                issuer=self._issuer,
                options={
                    "require_iss": True,
                    "require_exp": True,
                    "require_iat": True,
                },
            )
            return payload
        except JWTError as exc:
            # Translate JWT‑specific errors to a generic domain‑level error
            raise DomainError(f"Invalid token: {exc!s}") from exc

    def _create_token(
        self,
        user: User,
        *,
        token_type: str,
        lifetime: timedelta,
    ) -> str:
        """Common JWT‑minting logic for both token types."""
        now = datetime.now(UTC)
        expires = now + lifetime

        claims: dict[str, Any] = {
            # Registered claims (RFC 7519)
            "iss": self._issuer,
            "sub": user.id,
            "exp": int(expires.timestamp()),
            "iat": int(now.timestamp()),
            "jti": secrets.token_hex(16),  # unique identifier for this token
            # Private claims (our app‑specific data)
            "user_id": user.id,
            "username": user.username,
            "role": user.role,
            "token_type": token_type,
        }

        return jwt.encode(
            claims,
            self._secret_key,
            algorithm=ALGORITHMS.HS256,
        )


# Export only the concrete implementation
__all__ = ["JWTTokenService"]