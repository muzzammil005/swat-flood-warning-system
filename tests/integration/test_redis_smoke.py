"""Smoke test for Redis integration (requires live Redis container)."""

from __future__ import annotations

import pytest

from infrastructure.cache import RedisCacheAdapter


@pytest.mark.asyncio
@pytest.mark.integration
async def test_redis_smoke_connection() -> None:
    """Smoke test that verifies Redis adapter can connect to live Redis."""
    adapter = RedisCacheAdapter("redis://redis:6379/0")
    async with adapter:
        # Simple set/get to verify connection works
        await adapter.set("smoke:test", "success", ttl_seconds=10)
        value = await adapter.get("smoke:test")
        assert value == "success"
        await adapter.delete("smoke:test")


@pytest.mark.asyncio
@pytest.mark.integration 
async def test_redis_real_ttl() -> None:
    """Test real TTL behavior with live Redis."""
    import asyncio
    
    adapter = RedisCacheAdapter("redis://redis:6379/0")
    async with adapter:
        # Set with very short TTL
        await adapter.set("smoke:ttl", "expiring", ttl_seconds=2)
        
        # Should be there immediately
        value = await adapter.get("smoke:ttl")
        assert value == "expiring"
        
        # Wait for TTL to expire (plus a bit)
        await asyncio.sleep(3)
        
        # Should be gone after TTL
        value = await adapter.get("smoke:ttl")
        assert value is None