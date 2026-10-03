"""Unit tests for RedisCacheAdapter using fakeredis."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import fakeredis.aioredis as fakeredis
from infrastructure.cache import RedisCacheAdapter


@pytest.fixture
def fake_redis_client() -> fakeredis.FakeRedis:
    """Return a fake Redis client for testing."""
    return fakeredis.FakeRedis()


@pytest.fixture
def redis_adapter(fake_redis_client: fakeredis.FakeRedis) -> RedisCacheAdapter:
    """Return a RedisCacheAdapter with a fake Redis client."""
    adapter = RedisCacheAdapter("redis://fake:6379/0")
    
    # Patch the _ensure_client method to return our fake client
    async def mock_ensure_client():
        adapter._client = fake_redis_client
        return fake_redis_client
    
    adapter._ensure_client = mock_ensure_client
    return adapter


@pytest.mark.asyncio
async def test_get_set_delete(redis_adapter: RedisCacheAdapter) -> None:
    """Test basic get, set, and delete operations."""
    async with redis_adapter:
        # Set a value
        await redis_adapter.set("test:key1", "value1", ttl_seconds=30)
        
        # Get should return the value
        value = await redis_adapter.get("test:key1")
        assert value == "value1"
        
        # Delete should remove the key
        await redis_adapter.delete("test:key1")
        
        # Get after delete should return None
        value = await redis_adapter.get("test:key1")
        assert value is None


@pytest.mark.asyncio
async def test_get_nonexistent_key(redis_adapter: RedisCacheAdapter) -> None:
    """Test that non-existent keys return None."""
    async with redis_adapter:
        value = await redis_adapter.get("test:non_existent")
        assert value is None


@pytest.mark.asyncio
async def test_set_with_ttl(redis_adapter: RedisCacheAdapter) -> None:
    """Test setting values with TTL."""
    async with redis_adapter:
        # Set with TTL
        await redis_adapter.set("test:ttl", "expiring_value", ttl_seconds=10)
        
        # Should still be there
        value = await redis_adapter.get("test:ttl")
        assert value == "expiring_value"


@pytest.mark.asyncio
async def test_set_with_zero_ttl(redis_adapter: RedisCacheAdapter) -> None:
    """Test that zero or negative TTL is handled."""
    async with redis_adapter:
        # Set with zero TTL (should be treated as minimum 1 second)
        await redis_adapter.set("test:zero", "value", ttl_seconds=0)
        
        # Should still be stored
        value = await redis_adapter.get("test:zero")
        assert value == "value"


@pytest.mark.asyncio
async def test_special_characters(redis_adapter: RedisCacheAdapter) -> None:
    """Test that keys/values with special characters work."""
    async with redis_adapter:
        key = "test:key:with:colons"
        value = "value with spaces and спецсимволы 🚀"
        
        await redis_adapter.set(key, value, ttl_seconds=30)
        retrieved = await redis_adapter.get(key)
        assert retrieved == value


@pytest.mark.asyncio
async def test_redis_error_get_returns_none() -> None:
    """Test that Redis errors during get() return None (not raise)."""
    import redis.asyncio as redis
    
    adapter = RedisCacheAdapter("redis://fake:6379/0")
    
    # Mock a Redis error (must be RedisError or subclass to be caught)
    mock_client = AsyncMock()
    mock_client.get.side_effect = redis.RedisError("Redis connection failed")
    
    with patch.object(adapter, "_ensure_client", return_value=mock_client):
        async with adapter:
            value = await adapter.get("test:key")
            assert value is None


@pytest.mark.asyncio
async def test_redis_error_set_does_not_raise() -> None:
    """Test that Redis errors during set() don't raise exceptions."""
    import redis.asyncio as redis
    
    adapter = RedisCacheAdapter("redis://fake:6379/0")
    
    # Mock a Redis error (must be RedisError or subclass to be caught)
    mock_client = AsyncMock()
    mock_client.set.side_effect = redis.RedisError("Redis connection failed")
    
    with patch.object(adapter, "_ensure_client", return_value=mock_client):
        async with adapter:
            # Should not raise
            await adapter.set("test:key", "value", ttl_seconds=30)


@pytest.mark.asyncio
async def test_redis_error_delete_does_not_raise() -> None:
    """Test that Redis errors during delete() don't raise exceptions."""
    import redis.asyncio as redis
    
    adapter = RedisCacheAdapter("redis://fake:6379/0")
    
    # Mock a Redis error (must be RedisError or subclass to be caught)
    mock_client = AsyncMock()
    mock_client.delete.side_effect = redis.RedisError("Redis connection failed")
    
    with patch.object(adapter, "_ensure_client", return_value=mock_client):
        async with adapter:
            # Should not raise
            await adapter.delete("test:key")


@pytest.mark.asyncio
async def test_connection_failure_on_init() -> None:
    """Test that connection failure on init raises DomainError."""
    adapter = RedisCacheAdapter("redis://unreachable:6379/0")
    
    # Mock redis.from_url to raise an exception
    with patch("infrastructure.cache.redis_adapter.redis.from_url", side_effect=Exception("Connection refused")):
        with pytest.raises(Exception, match="Redis connection failed"):
            async with adapter:
                # Connection is lazy, so we need to trigger it
                await adapter.get("test:key")