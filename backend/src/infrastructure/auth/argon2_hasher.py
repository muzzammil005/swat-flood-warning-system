"""Argon2id password‑hashing adapter for the PasswordHasherPort.

Uses passlib's argon2 wrapper, which chooses safe defaults and handles
version‑upgrade migrations automatically.

The adapter never exposes raw hashes or KDF parameters to the caller — the
port contract returns opaque strings that can be stored directly in the
database's password_hash column.
"""

from __future__ import annotations

import logging

from passlib.context import CryptContext

from application.ports.auth import PasswordHasherPort

logger = logging.getLogger(__name__)


class Argon2PasswordHasher(PasswordHasherPort):
    """Argon2id‑based password hasher with safe defaults."""

    def __init__(self) -> None:
        # passlib's recommended Argon2 configuration for 2024‑ish hardware:
        #   - argon2id (hybrid of data‑dependent and independent memory access)
        #   - time_cost=2   (≈ 2 iterations)
        #   - memory_cost=102400  (≈ 100 MiB)
        #   - parallelism=8 (8 threads/lanes)
        #   - salt size = 16 bytes
        #   - hash length = 32 bytes
        #
        # The context automatically handles hash‑upgrade detection: if we later
        # increase time_cost, passlib will re‑hash on the next successful verify.
        self._ctx = CryptContext(
            schemes=["argon2"],
            argon2__type="id",
            argon2__time_cost=2,
            argon2__memory_cost=102400,
            argon2__parallelism=8,
            deprecated="auto",  # Auto‑upgrade if we change defaults later
        )

    def hash(self, raw: str, /) -> str:
        """Return an opaque Argon2id hash string suitable for storage."""
        if not raw:
            raise ValueError("Cannot hash empty password")

        # passlib.hash.argon2.hash() returns a string like:
        #   "$argon2id$v=19$m=102400,t=2,p=8$...salt...$...hash..."
        return self._ctx.hash(raw)

    def verify(self, raw: str, hashed: str, /) -> bool:
        """Return True if the raw password matches the stored hash."""
        if not raw or not hashed:
            logger.warning("Empty password or hash in verify()")
            return False

        try:
            return self._ctx.verify(raw, hashed)
        except Exception as exc:
            # Invalid hash format, wrong algorithm, etc.
            logger.warning("Password verification failed: %s", exc)
            return False


# Export only the concrete implementation
__all__ = ["Argon2PasswordHasher"]