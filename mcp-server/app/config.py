from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    KNOWBASE_API_URL: str
    KNOWBASE_API_KEY: str
    # No KNOWBASE_WORKSPACE_ID — the workspace is fixed by the API key itself.
    # Callers cannot override it; adding it here would imply a control that doesn't exist.
