from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ARES API"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://sentinel:sentinel@localhost:5432/sentinel"
    backend_cors_origins: list[str] = ["http://localhost:3000"]
    openai_api_key: str | None = None
    model_name: str | None = None
    upload_directory: str = "storage/uploads"
    max_upload_size: int = 25 * 1024 * 1024
    log_level: str = "INFO"
    debug: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
