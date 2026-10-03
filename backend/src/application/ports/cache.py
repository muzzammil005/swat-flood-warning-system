"""Key-value cache port with TTL expiry.

Implementations live in :mod:`infrastructure.cache` (Redis adapter in Prompt 6).
Used by Stage 3's use cases to short-circuit expensive calls — specifically:
- Weather forecast per zone (TTL ~ the provider's snapshot freshness window).
- Latest RiskAssessment per zone (TTL ~ the engine's cycle interval).

Values are *always* strings on the wire (JSON strings in practice). Callers
(never the cache adapter) are responsible for serialising domain objects to and
from cache-safe dicts — this keeps the cache adapter generic and prevents
domain object schemas from drifting silently.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class CachePort(ABC):
    """Simple string KV store with TTL-based expiry."""

    @abstractmethod
    async def get(self, key: str, /) -> str | None: ...

    @abstractmethod
    async def set(
        self, key: str, value: str, /, *, ttl_seconds: int
    ) -> None: ...

    @abstractmethod
    async def delete(self, key: str, /) -> None: ...
