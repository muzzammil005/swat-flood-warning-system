"""Redis adapter for the CachePort.

Uses redis[hiredis] async client (aioredis style) to implement the
CachePort's get/set/delete operations with TTL support.

The adapter expects a Redis instance reachable at the given URL (e.g.,
redis://localhost:6379/0). All values are stored as strings; serialisation
to/from JSON is the caller's responsibility (per the port contract).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import redis.asyncio as redis

from application.ports.cache import CachePort
from domain.exceptions.base import DomainError

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class RedisCacheAdapter(CachePort):
    """Redis‑backed implementation of the CachePort."""

    def __init__(
        self,
        redis_url: str,
        *,
        socket_connect_timeout: float = 5.0,
        socket_timeout: float = 5.0,
        max_connections: int = 10,
        health_check_interval: int = 30,
    ) -> None:
        """Initialise the Redis client pool.

        Args:
            redis_url: Connection URL (redis://host:port/db, redis://…/?ssl=True, etc.)
            socket_connect_timeout: How long to wait for a connection to be established
            socket_timeout: How long to wait for a command reply after sending it
            max_connections: Maximum number of connections in the pool
            health_check_interval: Seconds between background health checks
        """
        self._redis_url = redis_url
        self._client: Redis | None = None
        self._connection_kwargs = {
            "socket_connect_timeout": socket_connect_timeout,
            "socket_timeout": socket_timeout,
            "max_connections": max_connections,
            "health_check_interval": health_check_interval,
        }

    async def _ensure_client(self) -> Redis:
        """Lazy initialisation of the Redis client."""
        if self._client is None:
            try:
                self._client = redis.from_url(
                    self._redis_url,
                    **self._connection_kwargs,
                )
                # Quick ping to verify connectivity
                await self._client.ping()
                logger.debug(
                    "RedisCacheAdapter connected to %s", self._redis_url
                )
            except Exception as exc:
                logger.error(
                    "RedisCacheAdapter failed to connect to %s: %s",
                    self._redis_url,
                    exc,
                )
                raise DomainError(
                    f"Redis connection failed ({self._redis_url}): {exc!s}"
                ) from exc

        return self._client

    async def get(self, key: str, /) -> str | None:
        """Retrieve a string value by key, returning None on cache miss."""
        try:
            client = await self._ensure_client()
            value = await client.get(key)
            return value.decode("utf-8") if value is not None else None
        except (redis.RedisError, UnicodeDecodeError) as exc:
            # Log but don't crash the caller — treat Redis errors as cache misses
            logger.warning("Redis GET failed for key %r: %s", key, exc)
            return None

    async def set(self, key: str, value: str, /, *, ttl_seconds: int) -> None:
        """Store a string value with TTL‑based expiry."""
        if ttl_seconds <= 0:
            logger.warning(
                "Redis SET called with non‑positive TTL %d for key %r, "
                "value will expire immediately",
                ttl_seconds,
                key,
            )
            ttl_seconds = 1  # minimum 1‑second TTL

        try:
            client = await self._ensure_client()
            await client.set(key, value, ex=ttl_seconds)
        except redis.RedisError as exc:
            logger.warning(
                "Redis SET failed for key %r (ttl=%d): %s",
                key,
                ttl_seconds,
                exc,
            )
            # Don't raise — let the caller proceed without caching

    async def delete(self, key: str, /) -> None:
        """Remove a key from the cache."""
        try:
            client = await self._ensure_client()
            await client.delete(key)
        except redis.RedisError as exc:
            logger.warning("Redis DELETE failed for key %r: %s", key, exc)
            # Swallow the error; deletion is best‑effort

    async def close(self) -> None:
        """Close the Redis connection pool (call on shutdown)."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.debug("RedisCacheAdapter closed")

    async def __aenter__(self) -> RedisCacheAdapter:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()


# Export only the concrete implementation
__all__ = ["RedisCacheAdapter"]