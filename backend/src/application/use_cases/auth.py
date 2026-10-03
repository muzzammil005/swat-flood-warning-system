from dataclasses import dataclass
from typing import Any

from application.ports.auth import PasswordHasherPort, TokenPort
from domain.entities.user import User
from domain.exceptions import DomainError


class InvalidCredentialsError(DomainError):
    def __init__(self):
        super().__init__("Invalid username or password")


@dataclass(frozen=True)
class LoginResult:
    access_token: str
    user_id: str
    username: str
    role: str


class AuthUseCases:
    """Use cases for user authentication and authorization."""

    def __init__(
        self,
        hasher: PasswordHasherPort,
        token_service: TokenPort,
        session: Any,
    ):
        self.hasher = hasher
        self.token_service = token_service
        self.session = session

    async def login(self, username: str, password: str) -> LoginResult:
        """Authenticate user and issue tokens."""
        from sqlalchemy import select
        from infrastructure.db.models import UserModel

        stmt = select(UserModel).where(UserModel.username == username)
        result = await self.session.execute(stmt)
        user_model = result.scalar_one_or_none()

        if not user_model or not user_model.password_hash:
            raise InvalidCredentialsError()

        if not self.hasher.verify(password, user_model.password_hash):
            raise InvalidCredentialsError()

        # Create Domain User
        user = User(
            id=user_model.id,
            username=user_model.username,
            role=user_model.role.value,
            created_at=user_model.created_at,
        )

        access_token = self.token_service.issue_access_token(user)

        return LoginResult(
            access_token=access_token,
            user_id=user.id,
            username=user.username,
            role=user.role,
        )
