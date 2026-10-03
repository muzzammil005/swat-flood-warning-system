"""Minimal auth router for mobile login.

Temporary implementation for demo deadline.
Will be refactored into proper auth flow with RBAC after demo.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi import Request as FastAPIRequest
from sqlalchemy.ext.asyncio import AsyncSession

from application.use_cases.auth import AuthUseCases, InvalidCredentialsError
from infrastructure.auth.argon2_hasher import Argon2PasswordHasher
from infrastructure.auth.jwt_token_service import JWTTokenService
from infrastructure.config import get_settings
from infrastructure.db.session import get_session
from interfaces.http.rate_limiter import limiter
from interfaces.schemas.auth import LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
@limiter.limit("10/minute")
@limiter.limit("5/second")
async def login(
    request: FastAPIRequest,
    body: Annotated[LoginRequest, Body()],
) -> LoginResponse:
    """Login endpoint for issuing JWT tokens."""
    try:
        async with get_session() as session:
            settings = get_settings()
            token_service = JWTTokenService(
                secret_key=settings.jwt_secret_key.get_secret_value(),
                issuer=settings.jwt_issuer,
                access_token_lifetime_minutes=settings.access_token_expire_minutes,
            )
            hasher = Argon2PasswordHasher()
            
            use_cases = AuthUseCases(
                hasher=hasher,
                token_service=token_service,
                session=session,
            )
            
            result = await use_cases.login(body.username, body.password)
            return LoginResponse(
                access_token=result.access_token,
                token_type="bearer",
                user_id=result.user_id,
                username=result.username,
                role=result.role,
            )
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Login failed: {str(e)}"
        ) from e
