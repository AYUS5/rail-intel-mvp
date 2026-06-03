from functools import lru_cache

from app.api_client.http import AsyncHttpClient, AsyncHttpClientConfig, RetryPolicy
from app.core.config import get_settings
from app.provider_clients.railway_api_client import (
    RailwayProviderClient,
    RailwayProviderClientConfig,
)
from app.repositories.cached_railway_provider import CachedRailwayProvider
from app.repositories.fallback_railway_provider import FallbackRailwayProvider
from app.repositories.mock_railway_provider import MockRailwayProvider
from app.repositories.monitor_repository import InMemoryMonitorRepository, MonitorRepository
from app.repositories.railway_provider import RailwayProviderInterface
from app.repositories.real_railway_provider import RealRailwayProvider
from app.services.ai.explanation_service import AIExplanationService
from app.services.ai.providers import (
    OpenAIExplanationProvider,
    TemplateExplanationProvider,
)
from app.services.cache_service import (
    CacheService,
    CacheTTLConfig,
    InMemoryCacheBackend,
    RedisCacheBackend,
)
from app.services.monitoring_service import MonitoringService
from app.services.notification_service import NotificationService
from app.services.railway_service import RailwayService
from app.services.recommendation_service import RecommendationService
from app.services.route_analysis_service import RouteAnalysisConfig, RouteAnalysisService


@lru_cache
def get_cache_service() -> CacheService:
    settings = get_settings()
    backend = (
        RedisCacheBackend(settings.redis_url)
        if settings.cache_backend == "redis"
        else InMemoryCacheBackend()
    )
    return CacheService(
        backend,
        CacheTTLConfig(
            train_route_seconds=settings.route_cache_ttl_seconds,
            availability_seconds=settings.availability_cache_ttl_seconds,
            station_metadata_seconds=settings.station_cache_ttl_seconds,
        ),
    )


@lru_cache
def get_railway_provider() -> RailwayProviderInterface:
    settings = get_settings()
    mock_provider = MockRailwayProvider()

    if settings.railway_provider == "mock":
        provider: RailwayProviderInterface = mock_provider
    else:
        if not settings.real_provider_base_url:
            if settings.railway_provider == "real_with_mock_fallback":
                provider = mock_provider
            else:
                raise RuntimeError("REAL_PROVIDER_BASE_URL is required when RAILWAY_PROVIDER=real")
        else:
            http_client = AsyncHttpClient(
                AsyncHttpClientConfig(
                    base_url=settings.real_provider_base_url,
                    timeout_seconds=settings.real_provider_timeout_seconds,
                    max_connections=settings.real_provider_max_connections,
                    max_keepalive_connections=settings.real_provider_max_keepalive_connections,
                    api_key=settings.real_provider_api_key,
                    retry_policy=RetryPolicy(
                        max_attempts=settings.real_provider_max_retries,
                        base_backoff_seconds=settings.real_provider_retry_backoff_seconds,
                        max_backoff_seconds=settings.real_provider_max_retry_backoff_seconds,
                    ),
                )
            )
            provider_client = RailwayProviderClient(
                http_client,
                RailwayProviderClientConfig(
                    search_path=settings.real_provider_search_path,
                    route_path_template=settings.real_provider_route_path_template,
                    availability_path=settings.real_provider_availability_path,
                ),
            )
            real_provider = RealRailwayProvider(provider_client)
            provider = (
                FallbackRailwayProvider(real_provider, mock_provider)
                if settings.railway_provider == "real_with_mock_fallback"
                else real_provider
            )

    if settings.enable_provider_cache:
        return CachedRailwayProvider(provider, get_cache_service())
    return provider


@lru_cache
def get_monitor_repository_singleton() -> MonitorRepository:
    return InMemoryMonitorRepository()


def get_monitor_repository() -> MonitorRepository:
    return get_monitor_repository_singleton()


def get_railway_service() -> RailwayService:
    return RailwayService(get_railway_provider())


def get_route_analysis_service() -> RouteAnalysisService:
    settings = get_settings()
    return RouteAnalysisService(
        get_railway_service(),
        RouteAnalysisConfig(
            max_station_extension=settings.route_max_station_extension,
            min_overlap_ratio=settings.route_min_overlap_ratio,
            max_candidates_per_train=settings.route_max_candidates_per_train,
            availability_timeout_seconds=settings.route_availability_timeout_seconds,
            availability_concurrency=settings.route_availability_concurrency,
        ),
    )


@lru_cache
def get_recommendation_service() -> RecommendationService:
    return RecommendationService()


@lru_cache
def get_explanation_service() -> AIExplanationService:
    settings = get_settings()
    if settings.ai_provider == "openai" and settings.openai_api_key:
        provider = OpenAIExplanationProvider(settings.openai_api_key, settings.openai_model)
    else:
        provider = TemplateExplanationProvider()
    return AIExplanationService(provider)


@lru_cache
def get_notification_service() -> NotificationService:
    return NotificationService()


def get_monitoring_service() -> MonitoringService:
    return MonitoringService(
        repository=get_monitor_repository(),
        route_analysis_service=get_route_analysis_service(),
        recommendation_service=get_recommendation_service(),
        explanation_service=get_explanation_service(),
        notification_service=get_notification_service(),
    )
