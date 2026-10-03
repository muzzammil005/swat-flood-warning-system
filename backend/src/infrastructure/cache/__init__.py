"""Cache infrastructure adapters.

Exports the Redis concrete implementation from Prompt 6.
"""

from infrastructure.cache.redis_adapter import RedisCacheAdapter

__all__ = ["RedisCacheAdapter"]