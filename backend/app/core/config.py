"""Environment-driven application configuration."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str
    app_version: str
    environment: str
    api_v1_prefix: str
    database_url: str
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_api_key: str | None = None
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    llm_timeout_seconds: float = 8.0
    upload_directory: str
    log_level: str
    debug: bool
    max_upload_size: int
    cors_origins: list[str]
    trusted_hosts: list[str]
    vision_detector: str = "yolo"
    vision_model_path: str | None = None
    vision_confidence_threshold: float = 0.25
    vision_iou_threshold: float = 0.45
    vision_max_detections: int = 100
    vision_image_size: int = 640
    vision_device: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Return the immutable, process-wide configuration instance."""
    return Settings()
