from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    google_api_key: str | None = None
    adk_model: str = "gemini-2.5-flash"
    max_products: int = 20
    # Must match the directory that contains the root agent module (app/agents).
    app_name: str = "agents"


@lru_cache
def get_settings() -> Settings:
    return Settings()
