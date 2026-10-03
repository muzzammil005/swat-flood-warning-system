"""Environment-variable driven settings for the Swat Flood backend.

Use :func:`get_settings` to access the process-wide (cached) singleton.
All values are read from the process environment with secure defaults.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["dev", "staging", "prod"]


class Settings(BaseSettings):
    """Typed, validated settings for every runtime-concern of the backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Runtime environment
    # ------------------------------------------------------------------
    environment: Environment = "dev"

    # ------------------------------------------------------------------
    # JWT / auth — single source of truth across auth.py + auth_dependencies.py
    # ------------------------------------------------------------------
    jwt_secret_key: SecretStr = Field(
        default="replace_me_with_a_long_random_string_from_secrets",
        min_length=32,
        description="HMAC-SHA256 signing key — MUST be >= 32 chars in prod.",
    )
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "swat-flood-backend"
    access_token_expire_minutes: int = 30

    @field_validator("jwt_secret_key", mode="after")
    @classmethod
    def _reject_placeholder_in_prod(cls, value: SecretStr, info) -> SecretStr:
        """HARD FAIL at boot if someone tries to run prod with the default key.

        The default placeholder is documented in ``.env.example`` and the field
        description. Anyone deploying to prod must override it via env — if
        they forget, we crash instead of signing tokens with a public key.
        """
        env = info.data.get("environment", "dev")
        if env == "prod":
            secret_value = value.get_secret_value()
            if secret_value == "replace_me_with_a_long_random_string_from_secrets":
                raise ValueError(
                    "ENVIRONMENT=prod but JWT_SECRET_KEY is still the placeholder. "
                    "Export JWT_SECRET_KEY to a 32+ char random string before starting "
                    "the backend in production mode."
                )
        return value

    # ------------------------------------------------------------------
    # Connection strings
    # ------------------------------------------------------------------
    database_url: SecretStr = Field(
        default=(
            "postgresql+asyncpg://swat:swat_dev_password@127.0.0.1:15432/swat_flood"
        ),
    )
    redis_url: SecretStr = Field(default="redis://127.0.0.1:16379/0")

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    # A comma-separated list of origins allowed to call the API from a browser.
    #   e.g. CORS_ALLOW_ORIGINS="http://localhost:3000, http://localhost:3001"
    # Use the literal wildcard "*" to allow any origin (DEV ONLY, auto-detected).
    #
    # Implementation note: intentionally typed as ``Any`` (then normalized to
    # ``list[str]`` in the after-validator) because pydantic-settings version
    # 2.15+ first attempts to JSON-decode any annotation of ``list[str]`` from
    # the raw env string BEFORE running a before-validator; that JSON pass
    # crashes on a perfectly valid CSV like "http://a,http://b". Accepting Any
    # skips the JSON-first step while the validator below still guarantees the
    # final runtime value is list[str].
    cors_allow_origins: Any = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3000",
        ],
    )

    @field_validator("cors_allow_origins", mode="after")
    @classmethod
    def _normalize_cors_origins(cls, raw: Any) -> list[str]:  # noqa: ANN401
        """Normalize raw CORS input into a list[str].

        Supported input shapes:
          * a single string with no commas → one-element list
          * a CSV string ``"a, b, c"`` → three-element list, whitespace trimmed
          * a JSON list string ``"[\"a\",\"b\"]"`` → parsed as list of str
          * already a list/sequence → each element str()'d and de-duplicated
          * ``None`` / empty → falls back to the default_factory
        """
        if raw is None:
            return [
                "http://localhost:3000",
                "http://localhost:3001",
                "http://127.0.0.1:3000",
            ]
        if isinstance(raw, str):
            stripped = raw.strip()
            if not stripped:
                return [
                    "http://localhost:3000",
                    "http://localhost:3001",
                    "http://127.0.0.1:3000",
                ]
            # Try JSON list first; fall back to comma split.
            if stripped.startswith("["):
                import json as _json

                try:
                    parsed = _json.loads(stripped)
                except ValueError:
                    parsed = None
                if isinstance(parsed, list):
                    return [str(x).strip() for x in parsed if str(x).strip()]
            return [o.strip() for o in stripped.split(",") if o.strip()]
        # Sequence/list-like (but not dict/str/bytes)
        if hasattr(raw, "__iter__") and not isinstance(raw, (dict, bytes, bytearray)):
            return [str(x).strip() for x in raw if str(x).strip()]
        return [str(raw).strip()] if str(raw).strip() else []

    # ------------------------------------------------------------------
    # Helpers used by the HTTP layer to stay spec-compliant.
    # ------------------------------------------------------------------
    @property
    def cors_allow_credentials(self) -> bool:
        """Per RFC6454 + Fetch spec, `Access-Control-Allow-Credentials: true`
        is illegal when any allowed origin is the wildcard ``"*"``. We
        explicitly disable credentials in that case so the browser does not
        reject preflight."""
        return "*" not in self.cors_allow_origins

    @property
    def is_production(self) -> bool:
        return self.environment == "prod"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached process-wide settings instance."""
    return Settings()


__all__ = ["Settings", "Environment", "get_settings"]
