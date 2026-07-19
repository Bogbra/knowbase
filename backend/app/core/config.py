import secrets
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_NAME: str = "Knowbase"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    # Empty by default — the after-validator below auto-generates one for dev/staging
    # convenience but *requires* an operator-set value in production. A silent
    # per-process random default in prod would invalidate all JWTs on every restart
    # and make multi-instance deployments reject each other's tokens.
    SECRET_KEY: str = ""

    # API
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_ORIGINS: list[str] = []

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            # Accept JSON array ("["url"]") or comma-separated string
            stripped = v.strip()
            if stripped.startswith("["):
                import json

                return list[str](json.loads(stripped))
            return [o.strip() for o in stripped.split(",") if o.strip()]
        return v

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/knowbase"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fix_db_url(cls, v: object) -> str:
        s = str(v)
        if s.startswith("postgres://"):
            return s.replace("postgres://", "postgresql+asyncpg://", 1)
        if s.startswith("postgresql://"):
            return s.replace("postgresql://", "postgresql+asyncpg://", 1)
        return s

    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Auth
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # Rate limiting (requests per minute)
    RATE_LIMIT_PER_MINUTE: int = 60
    # Set True when the app runs behind a trusted reverse proxy (Railway, Fly, nginx).
    # When False, X-Real-IP / X-Forwarded-For headers are ignored — clients on a
    # directly reachable port could otherwise spoof any IP and bypass rate limits.
    TRUST_PROXY_HEADERS: bool = False

    # AI APIs
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = ""

    # Agent
    AGENT_MODEL: str = "claude-sonnet-4-6"
    AGENT_FALLBACK_MODEL: str = "claude-haiku-4-5-20251001"
    OPENAI_AGENT_MODEL: str = "gpt-4o"
    OPENAI_AGENT_FALLBACK_MODEL: str = "gpt-4o-mini"
    AGENT_MAX_TOKENS: int = 4096
    AGENT_TOKEN_BUDGET: int = 100_000
    AGENT_MEMORY_K: int = 5
    AGENT_RETRIEVAL_DISTANCE_THRESHOLD: float = 0.3

    # Web search
    TAVILY_API_KEY: str = ""

    # SSE
    SSE_STREAM_TTL_S: int = 3600

    # Storage (S3-compatible)
    S3_ENDPOINT_URL: str = ""
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET_NAME: str = "knowbase"
    S3_REGION: str = "us-east-1"

    # File uploads
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB

    # Sentry
    SENTRY_DSN: str = ""

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @model_validator(mode="after")
    def _require_operator_set_secrets_in_production(self) -> "Settings":
        if self.ENVIRONMENT != "production":
            # Dev/staging convenience: a fresh key per process is fine — nobody
            # depends on token continuity across restarts in these environments.
            if not self.SECRET_KEY:
                self.SECRET_KEY = secrets.token_urlsafe(32)
            return self

        if not self.SECRET_KEY:
            raise ValueError(
                "SECRET_KEY must be set via env var when ENVIRONMENT=production. "
                "Refusing to boot with an auto-generated key: every process restart "
                "would invalidate all JWTs, and each instance behind a load balancer "
                "would reject tokens issued by the others."
            )

        if bool(self.S3_ACCESS_KEY_ID) != bool(self.S3_SECRET_ACCESS_KEY):
            raise ValueError(
                "S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY must both be set (or both "
                "unset) in production. A partial S3 config silently falls back to "
                "signing requests without a secret, failing only on first upload."
            )

        if not self.ALLOWED_ORIGINS:
            raise ValueError(
                "ALLOWED_ORIGINS must be set via env var when ENVIRONMENT=production. "
                "An empty list silently blocks every browser request, including the "
                "real frontend, rather than failing loudly at boot."
            )

        return self


settings = Settings()
