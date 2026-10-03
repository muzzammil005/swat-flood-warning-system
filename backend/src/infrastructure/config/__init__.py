"""Runtime configuration (env-driven).

Single source of truth for secrets, feature flags, and deployment settings.
Consumed by HTTP layer (auth, CORS), token service, DB/Redis connection setup.
"""

from .settings import Settings, get_settings

__all__ = ["Settings", "get_settings"]
