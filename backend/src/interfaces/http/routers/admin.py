"""Admin-only endpoints for manual overrides, resource centers, and user management.

Endpoints:
- POST /api/admin/overrides        — create manual override (admin only)
- GET  /api/admin/overrides        — list overrides for a zone (admin only)
- GET  /api/resource-centers       — public resource center listing
- POST /api/admin/users            — create operator account (admin only)
- GET  /api/admin/users            — list all users (admin only)
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from application.use_cases.admin import AdminUseCases, InvalidRiskTierError, UserAlreadyExistsError
from application.use_cases.resource_centers import ResourceCenterUseCases
from infrastructure.db.repositories import (
    AuditLogRepositoryImpl,
    InventoryItemRepositoryImpl,
    ManualOverrideRepositoryImpl,
    ResourceCenterRepositoryImpl,
    UserRepositoryImpl,
)
from infrastructure.db.session import get_session
from interfaces.http.auth_dependencies import require_admin

router = APIRouter(tags=["admin"])

# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class OverrideRequest(BaseModel):
    zone_id: str
    threat_level: str   # LOW | MEDIUM | HIGH
    reason: str

    @field_validator("threat_level", mode="before")
    @classmethod
    def validate_threat_level(cls, value: object) -> str:
        if hasattr(value, "value"):
            val_str = str(value.value)
        elif hasattr(value, "name"):
            val_str = str(value.name)
        else:
            val_str = str(value)
        val_upper = val_str.upper()
        if val_upper not in ("LOW", "MEDIUM", "HIGH"):
            raise ValueError(f"Invalid threat_level '{val_str}'. Must be one of: LOW, MEDIUM, HIGH")
        return val_upper


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: Literal["admin", "responder"] = "responder"


# ---------------------------------------------------------------------------
# Manual Overrides
# ---------------------------------------------------------------------------

@router.post("/admin/overrides")
async def create_manual_override(
    body: OverrideRequest,
    current_user: Annotated[dict, Depends(require_admin)],
) -> dict:
    """Force a zone's displayed risk tier.

    The most-recent override for a zone is treated as 'active'.
    Requires admin JWT.
    """
    admin_username = current_user.get("username", "unknown")
    try:
        async with get_session() as session:
            override_repo = ManualOverrideRepositoryImpl(session)
            audit_repo = AuditLogRepositoryImpl(session)
            user_repo = UserRepositoryImpl(session)
            use_cases = AdminUseCases(
                override_repo=override_repo,
                audit_repo=audit_repo,
                user_repo=user_repo,
                session_maker=session,
            )

            saved = await use_cases.create_manual_override(
                zone_id=body.zone_id,
                threat_level=body.threat_level,
                reason=body.reason,
                admin_username=admin_username,
            )
            
            # Commit manually since use_cases.session is injected but not committed
            await use_cases.session.commit()

            threat_str = saved.threat_level.name if hasattr(saved.threat_level, "name") else (saved.threat_level.value if hasattr(saved.threat_level, "value") else str(saved.threat_level))

            return {
                "id": saved.id,
                "zone_id": saved.zone_id,
                "threat_level": threat_str,
                "reason": saved.reason,
                "admin_username": saved.admin_username,
                "timestamp": saved.timestamp.isoformat(),
            }
    except InvalidRiskTierError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create manual override: {exc}",
        ) from exc


@router.get("/admin/overrides")
async def list_overrides(
    current_user: Annotated[dict, Depends(require_admin)],
    zone_id: str | None = None,
) -> list[dict]:
    """List manual overrides for a zone (or all if zone_id is missing), most recent first.

    Requires admin JWT.
    """
    try:
        async with get_session() as session:
            override_repo = ManualOverrideRepositoryImpl(session)
            audit_repo = AuditLogRepositoryImpl(session)
            user_repo = UserRepositoryImpl(session)
            from infrastructure.db.repositories import ZoneRepositoryImpl
            zone_repo = ZoneRepositoryImpl(session)
            
            use_cases = AdminUseCases(
                override_repo=override_repo,
                audit_repo=audit_repo,
                user_repo=user_repo,
                session_maker=session,
            )

            overrides = await use_cases.list_zone_overrides(zone_id)
            
            # Find which overrides are active (most recent per zone)
            active_override_ids = set()
            zones = await zone_repo.list_all()
            zone_names = {z.id: z.name for z in zones}
            
            for z in zones:
                active = await override_repo.active_for_zone(z.id)
                if active:
                    active_override_ids.add(active.id)
            
            return [
                {
                    "id": o.id,
                    "zone_id": o.zone_id,
                    "zone_name": zone_names.get(o.zone_id, "Unknown Zone"),
                    "threat_level": o.threat_level.name if hasattr(o.threat_level, "name") else (o.threat_level.value if hasattr(o.threat_level, "value") else str(o.threat_level)),
                    "reason": o.reason,
                    "created_by_username": o.admin_username,
                    "created_at": o.timestamp.isoformat(),
                    "is_active": o.id in active_override_ids,
                }
                for o in overrides
            ]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list overrides: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# Resource Centers (public)
# ---------------------------------------------------------------------------

@router.get("/resource-centers")
async def get_resource_centers() -> list[dict]:
    """Return all resource centers with their inventory.

    Public endpoint — used by the 'Active Relief Centers' dashboard panel.
    No auth required.
    """
    try:
        async with get_session() as session:
            center_repo = ResourceCenterRepositoryImpl(session)
            item_repo = InventoryItemRepositoryImpl(session)
            use_cases = ResourceCenterUseCases(center_repo, item_repo)

            details = await use_cases.get_all_centers()
            return [
                {
                    "id": d.center.id,
                    "name": d.center.name,
                    "location_zone": d.center.location_zone,
                    "inventory": [
                        {
                            "id": item.id,
                            "item_name": item.item_name,
                            "quantity": item.quantity,
                        }
                        for item in d.inventory
                    ],
                }
                for d in details
            ]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch resource centers: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# User management (admin only)
# ---------------------------------------------------------------------------

@router.post("/admin/users")
async def create_user(
    body: CreateUserRequest,
    current_user: Annotated[dict, Depends(require_admin)],
) -> dict:
    """Create a new operator account.

    Rejects duplicate usernames with HTTP 400.
    Requires admin JWT.
    """
    try:
        async with get_session() as session:
            override_repo = ManualOverrideRepositoryImpl(session)
            audit_repo = AuditLogRepositoryImpl(session)
            user_repo = UserRepositoryImpl(session)
            use_cases = AdminUseCases(
                override_repo=override_repo,
                audit_repo=audit_repo,
                user_repo=user_repo,
                session_maker=session,
            )

            user = await use_cases.create_user(
                username=body.username,
                password=body.password,
                role=body.role,
            )
            await use_cases.session.commit()
            
            return {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "created_at": user.created_at.isoformat(),
            }
    except UserAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {exc}",
        ) from exc


@router.get("/admin/users")
async def list_users(
    current_user: Annotated[dict, Depends(require_admin)],
) -> list[dict]:
    """List all users without password_hash.

    Requires admin JWT.
    """
    try:
        async with get_session() as session:
            override_repo = ManualOverrideRepositoryImpl(session)
            audit_repo = AuditLogRepositoryImpl(session)
            user_repo = UserRepositoryImpl(session)
            use_cases = AdminUseCases(
                override_repo=override_repo,
                audit_repo=audit_repo,
                user_repo=user_repo,
                session_maker=session,
            )

            users = await use_cases.list_users()
            return [
                {
                    "id": u.id,
                    "username": u.username,
                    "role": u.role,
                    "created_at": u.created_at.isoformat(),
                }
                for u in users
            ]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list users: {exc}",
        ) from exc


class ResetPasswordRequest(BaseModel):
    new_password: str


@router.post("/admin/users/{user_id}/reset-password")
async def reset_password(
    user_id: str,
    body: ResetPasswordRequest,
    current_user: Annotated[dict, Depends(require_admin)],
) -> dict:
    """Reset a user's password.

    Requires admin JWT.
    """
    admin_username = current_user.get("username", "unknown")
    try:
        async with get_session() as session:
            override_repo = ManualOverrideRepositoryImpl(session)
            audit_repo = AuditLogRepositoryImpl(session)
            user_repo = UserRepositoryImpl(session)
            use_cases = AdminUseCases(
                override_repo=override_repo,
                audit_repo=audit_repo,
                user_repo=user_repo,
                session_maker=session,
            )

            await use_cases.reset_user_password(
                user_id=user_id,
                new_password=body.new_password,
                admin_username=admin_username,
            )
            await use_cases.session.commit()
            
            return {"status": "success", "message": "Password reset successfully"}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset password: {exc}",
        ) from exc


@router.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: Annotated[dict, Depends(require_admin)],
) -> dict:
    """Delete a user.

    Requires admin JWT.
    """
    admin_username = current_user.get("username", "unknown")
    try:
        async with get_session() as session:
            override_repo = ManualOverrideRepositoryImpl(session)
            audit_repo = AuditLogRepositoryImpl(session)
            user_repo = UserRepositoryImpl(session)
            use_cases = AdminUseCases(
                override_repo=override_repo,
                audit_repo=audit_repo,
                user_repo=user_repo,
                session_maker=session,
            )

            await use_cases.delete_user(
                user_id=user_id,
                admin_username=admin_username,
            )
            await use_cases.session.commit()
            
            return {"status": "success", "message": "User deleted successfully"}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {exc}",
        ) from exc
