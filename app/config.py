from functools import lru_cache
import os

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
    # Parallel fan-out uses more RAM; keep off on Render free instances.
    aeo_parallel: bool = False

    def resolved_google_api_key(self) -> str | None:
        return self.google_api_key or os.environ.get("GOOGLE_API_KEY") or None


@lru_cache
def get_settings() -> Settings:
    return Settings()
