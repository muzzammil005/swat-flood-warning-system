"""FastAPI dependencies for JWT authentication and role-based access control.

This module provides:
- get_current_user: Verifies Authorization: Bearer <token> header and returns user claims
- require_admin: Requires authenticated user with "admin" role
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from domain.exceptions.base import DomainError
from infrastructure.auth.jwt_token_service import JWTTokenService
from infrastructure.config import get_settings

security_scheme = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security_scheme)]
) -> dict:
    """Dependency that verifies JWT token and returns decoded user claims.
    
    Raises:
        HTTPException: 401 if token is missing/invalid/expired
    """
    try:
        settings = get_settings()
        token_service = JWTTokenService(
            secret_key=settings.jwt_secret_key.get_secret_value(),
            issuer=settings.jwt_issuer,
        )
        claims = token_service.verify_token(credentials.credentials)
        
        # Ensure token_type is "access" (not refresh token)
        if claims.get("token_type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        return claims
    except DomainError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        ) from e


from typing import Callable

def require_role(allowed_roles: list[str]) -> Callable:
    """Dependency factory for checking user roles.
    
    Args:
        allowed_roles: List of roles that are allowed to access the endpoint.
        
    Returns:
        A dependency that can be used in FastAPI routes.
    """
    async def role_checker(
        current_user: Annotated[dict, Depends(get_current_user)]
    ) -> dict:
        user_role = current_user.get("role")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Allowed roles: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker


# Legacy aliases for convenience
async def require_admin(
    current_user: Annotated[dict, Depends(require_role(["admin"]))]
) -> dict:
    """Dependency that requires authenticated user with "admin" role."""
    return current_user


# Export dependencies for use in routers
__all__ = ["get_current_user", "require_role", "require_admin"]