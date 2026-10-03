"""Auth-related Pydantic schemas for HTTP responses.

Temporary MVP schemas for demo deadline.
Will be refined and moved to proper DTO layer after demo.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    """Request schema for login."""
    username: str
    password: str
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "admin",
                "password": "admin123"
            }
        }
    )


class LoginResponse(BaseModel):
    """Response schema for successful login."""
    access_token: str
    token_type: str
    user_id: str
    username: str
    role: str
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIs...",
                "token_type": "bearer",
                "user_id": "user_123",
                "username": "admin",
                "role": "admin"
            }
        }
    )
