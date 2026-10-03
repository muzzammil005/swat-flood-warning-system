"""Global rate limiter singleton.

Extracted into its own module to break the circular import that would
otherwise exist between ``main.py`` (which imports routers) and the
router modules (which each need to apply the ``@limiter.limit`` decorator
and therefore need a reference to the limiter object).

Instead of:
    main -> routers.auth -> main (imports limiter)  -> CIRCULAR

We now have:
    main -> rate_limiter (limiter defined here)
    routers.auth -> rate_limiter       -> NO CYCLE
"""

from __future__ import annotations

from ipaddress import ip_address
from typing import TYPE_CHECKING

from slowapi import Limiter
from slowapi.util import get_remote_address

if TYPE_CHECKING:
    from fastapi import Request


def _get_client_ip(request: Request) -> str:
    """Rate-limit key: use X-Forwarded-For first, else remote client IP.

    This makes rate limiting accurate behind a reverse proxy (Caddy, nginx,
    traefik) that sets X-Forwarded-For to the real client IP. Falls back to
    ``get_remote_address`` for direct connections (dev / docker). Validates
    the parsed IP before using it to prevent header-poisoned buckets.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first_ip = forwarded.split(",")[0].strip()
        try:
            ip_address(first_ip)
            return first_ip
        except ValueError:
            pass
    return get_remote_address(request)


# Global limiter singleton. Deployments that scale to multiple backend
# processes should swap to a Redis backend via slowapi's `Limiter(
# storage_uri="redis://...")` constructor.
limiter: Limiter = Limiter(key_func=_get_client_ip)

__all__ = ["limiter", "_get_client_ip"]
