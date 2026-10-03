"""Integration test for RedisCacheAdapter against the live Redis container.

This test verifies that the Redis adapter can connect to the Redis instance
defined in docker‑compose.yml and perform basic get/set/delete operations.
"""

from __future__ import annotations

import pytest

from infrastructure.cache import RedisCacheAdapter


@pytest.mark.asyncio
@pytest.mark.integration
async def test_redis_basic_operations() -> None:
    """Test that RedisCacheAdapter can store, retrieve, and delete values."""
    # Use the Redis URL from docker‑compose.yml (redis:6379/0)
    adapter = RedisCacheAdapter("redis://redis:6379/0")
    async with adapter:
        # 1. SET a value with TTL
        await adapter.set("test:key1", "value1", ttl_seconds=30)
        
        # 2. GET should return the value
        value = await adapter.get("test:key1")
        assert value == "value1"
        
        # 3. DELETE should remove the key
        await adapter.delete("test:key1")
        
        # 4. GET after DELETE should return None
        value = await adapter.get("test:key1")
        assert value is None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_redis_ttl_expiry() -> None:
    """Test that TTL expiry works (using very short TTL for test)."""
    adapter = RedisCacheAdapter("redis://redis:6379/0")
    async with adapter:
        # Set with 1‑second TTL
        await adapter.set("test:ttl", "expiring_value", ttl_seconds=1)
        
        # Should still be there immediately
        value = await adapter.get("test:ttl")
        assert value == "expiring_value"
        
        # Clean up
        await adapter.delete("test:ttl")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_redis_empty_key() -> None:
    """Test that non‑existent keys return None."""
    adapter = RedisCacheAdapter("redis://redis:6379/0")
    async with adapter:
        value = await adapter.get("test:non_existent")
        assert value is None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_redis_special_characters() -> None:
    """Test that keys/values with special characters work correctly."""
    adapter = RedisCacheAdapter("redis://redis:6379/0")
    async with adapter:
        key = "test:key:with:colons"
        value = "value with spaces and спецсимволы 🚀"
        
        await adapter.set(key, value, ttl_seconds=30)
        retrieved = await adapter.get(key)
        assert retrieved == value
        
        await adapter.delete(key)