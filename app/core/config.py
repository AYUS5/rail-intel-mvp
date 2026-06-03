from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Rail Intel MVP"
    environment: Literal["local", "test", "staging", "production"] = "local"
    log_level: str = "INFO"

    database_url: str = Field(
        default="postgresql+asyncpg://railintel:railintel@postgres:5432/railintel"
    )
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    railway_provider: Literal["mock", "real", "real_with_mock_fallback"] = "mock"
    real_provider_base_url: str | None = None
    real_provider_api_key: str | None = None
    real_provider_timeout_seconds: float = 5.0
    real_provider_max_retries: int = 3
    real_provider_max_connections: int = 100
    real_provider_max_keepalive_connections: int = 20
    real_provider_retry_backoff_seconds: float = 0.25
    real_provider_max_retry_backoff_seconds: float = 2.0
    real_provider_search_path: str = "/trains/search"
    real_provider_route_path_template: str = "/trains/{train_number}/route"
    real_provider_availability_path: str = "/availability"
    enable_provider_cache: bool = True
    cache_backend: Literal["memory", "redis"] = "memory"
    route_cache_ttl_seconds: int = 60 * 60 * 24
    availability_cache_ttl_seconds: int = 60
    station_cache_ttl_seconds: int = 60 * 60 * 24 * 7
    monitor_repository: Literal["memory", "postgres"] = "memory"

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    ai_provider: Literal["template", "openai"] = "template"

    route_max_station_extension: int = 2
    route_min_overlap_ratio: float = 0.35
    route_max_candidates_per_train: int = 12
    route_availability_timeout_seconds: float = 8.0
    route_availability_concurrency: int = 12

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
