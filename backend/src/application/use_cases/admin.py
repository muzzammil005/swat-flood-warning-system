import uuid
from datetime import UTC, datetime

from application.ports.repositories import (
    AuditLogRepository,
    ManualOverrideRepository,
    UserRepository,
)
from domain.entities.audit_log_entry import AuditLogEntry
from domain.entities.manual_override import ManualOverride
from domain.entities.user import User
from domain.exceptions import DomainError
from domain.value_objects.risk_tier import RiskTier
from infrastructure.auth.argon2_hasher import Argon2PasswordHasher
from infrastructure.db.models import DBUserRole
from sqlalchemy import insert


class UserAlreadyExistsError(DomainError):
    def __init__(self, username: str):
        super().__init__(f"Username '{username}' already exists")


class InvalidRiskTierError(DomainError):
    def __init__(self, tier_name: str):
        super().__init__(f"Invalid threat_level '{tier_name}'. Must be one of: LOW, MEDIUM, HIGH")


class AdminUseCases:
    """Use cases for administrative operations."""

    def __init__(
        self,
        override_repo: ManualOverrideRepository,
        audit_repo: AuditLogRepository,
        user_repo: UserRepository,
        session_maker,  # To handle custom insert for User since UserRepository might lack `add`
    ):
        self.override_repo = override_repo
        self.audit_repo = audit_repo
        self.user_repo = user_repo
        self.session = session_maker

    async def create_manual_override(
        self, zone_id: str, threat_level: str | RiskTier | object, reason: str, admin_username: str
    ) -> ManualOverride:
        """Force a zone's displayed risk tier and log the action."""
        if hasattr(threat_level, "value") and isinstance(threat_level.value, str):
            tier_name = threat_level.value.upper()
        elif hasattr(threat_level, "name"):
            tier_name = threat_level.name.upper()
        else:
            tier_name = str(threat_level).upper()

        try:
            if tier_name not in ("LOW", "MEDIUM", "HIGH"):
                raise KeyError(tier_name)
            tier = RiskTier[tier_name]
        except (KeyError, ValueError) as e:
            raw_display = threat_level.value if hasattr(threat_level, "value") else (threat_level.name if hasattr(threat_level, "name") else str(threat_level))
            raise InvalidRiskTierError(str(raw_display)) from e

        override = ManualOverride(
            id=f"override-{uuid.uuid4()}",
            zone_id=zone_id,
            threat_level=tier,
            reason=reason,
            admin_username=admin_username,
            timestamp=datetime.now(UTC),
        )
        saved = await self.override_repo.add(override)

        entry = AuditLogEntry(
            id=f"audit-{uuid.uuid4()}",
            actor_username=admin_username,
            action="manual_override_created",
            target=f"zone:{zone_id}",
            timestamp=datetime.now(UTC),
        )
        await self.audit_repo.add(entry)

        return saved

    async def list_zone_overrides(self, zone_id: str | None = None) -> list[ManualOverride]:
        """List all manual overrides for a specific zone, or all if zone_id is None."""
        # We might need to fetch directly from repo since it might not have list_for_zone
        from sqlalchemy import select
        from infrastructure.db.models import ManualOverrideModel
        from infrastructure.db.mappers import manual_override_to_domain

        stmt = select(ManualOverrideModel).order_by(ManualOverrideModel.timestamp.desc())
        if zone_id:
            stmt = stmt.where(ManualOverrideModel.zone_id == zone_id)
            
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        
        return [manual_override_to_domain(row) for row in rows]

    async def create_user(
        self, username: str, password: str, role: str
    ) -> User:
        """Create a new operator or admin account."""
        existing = await self.user_repo.get_by_username(username)
        if existing:
            raise UserAlreadyExistsError(username)

        hasher = Argon2PasswordHasher()
        password_hash = hasher.hash(password)
        user_id = f"user-{uuid.uuid4()}"
        created_at = datetime.now(UTC)

        from infrastructure.db.models import UserModel
        stmt = insert(UserModel).values(
            id=user_id,
            username=username,
            password_hash=password_hash,
            role=DBUserRole(role),
            created_at=created_at,
        )
        await self.session.execute(stmt)

        return User(
            id=user_id,
            username=username,
            role=role,
            created_at=created_at,
        )

    async def list_users(self) -> list[User]:
        """List all users in the system."""
        return await self.user_repo.list_all()

    async def reset_user_password(
        self, user_id: str, new_password: str, admin_username: str
    ) -> None:
        """Securely hash and update a user's password, bypassing append-only repository."""
        existing = await self.user_repo.get_by_id(user_id)
        if not existing:
            raise DomainError(f"User {user_id} not found")

        hasher = Argon2PasswordHasher()
        password_hash = hasher.hash(new_password)

        from infrastructure.db.models import UserModel
        from sqlalchemy import update
        stmt = update(UserModel).where(UserModel.id == user_id).values(password_hash=password_hash)
        await self.session.execute(stmt)

        entry = AuditLogEntry(
            id=f"audit-{uuid.uuid4()}",
            actor_username=admin_username,
            action="admin_reset_user_password",
            target=f"user:{user_id}",
            timestamp=datetime.now(UTC),
        )
        await self.audit_repo.add(entry)

    async def delete_user(self, user_id: str, admin_username: str) -> None:
        """Delete a user from the system."""
        existing = await self.user_repo.get_by_id(user_id)
        if not existing:
            raise DomainError(f"User {user_id} not found")

        from infrastructure.db.models import UserModel
        from sqlalchemy import delete
        stmt = delete(UserModel).where(UserModel.id == user_id)
        await self.session.execute(stmt)

        entry = AuditLogEntry(
            id=f"audit-{uuid.uuid4()}",
            actor_username=admin_username,
            action="admin_delete_user",
            target=f"user:{user_id}",
            timestamp=datetime.now(UTC),
        )
        await self.audit_repo.add(entry)
