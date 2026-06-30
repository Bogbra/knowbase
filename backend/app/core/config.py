import secrets
from typing import Literal

from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_NAME: str = "Knowbase"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    SECRET_KEY: str = secrets.token_urlsafe(32)

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
    DATABASE_URL: PostgresDsn = PostgresDsn(
        "postgresql+asyncpg://postgres:postgres@localhost:5432/knowbase"
    )
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


settings = Settings()
