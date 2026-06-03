import asyncio
import time
from datetime import date

import pytest

from app.repositories.cached_railway_provider import CachedRailwayProvider
from app.repositories.mock_railway_provider import MockRailwayProvider
from app.schemas.common import TravelClass
from app.services.cache_service import CacheService, CacheTTLConfig, InMemoryCacheBackend
from app.services.railway_service import RailwayService
from app.services.route_analysis_service import RouteAnalysisConfig, RouteAnalysisService


class SlowCountingProvider(MockRailwayProvider):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0
        self.inflight = 0
        self.max_inflight = 0

    async def get_availability(self, *args, **kwargs):
        self.calls += 1
        self.inflight += 1
        self.max_inflight = max(self.max_inflight, self.inflight)
        try:
            await asyncio.sleep(0.02)
            return await super().get_availability(*args, **kwargs)
        finally:
            self.inflight -= 1


@pytest.mark.asyncio
async def test_route_analysis_fetches_candidate_availability_concurrently() -> None:
    provider = SlowCountingProvider()
    service = RouteAnalysisService(
        RailwayService(provider),
        RouteAnalysisConfig(
            max_station_extension=2,
            min_overlap_ratio=0.25,
            max_candidates_per_train=10,
            availability_concurrency=4,
            availability_timeout_seconds=2,
        ),
    )

    start = time.perf_counter()
    analyses = await service.analyze_search(
        "Delhi",
        "Mumbai",
        date(2026, 6, 15),
        TravelClass.THIRD_AC,
        max_results=1,
    )
    duration = time.perf_counter() - start

    assert analyses
    assert provider.max_inflight > 1
    assert duration < provider.calls * 0.02


@pytest.mark.asyncio
async def test_cached_provider_avoids_duplicate_upstream_availability_requests() -> None:
    provider = SlowCountingProvider()
    cache = CacheService(
        InMemoryCacheBackend(),
        CacheTTLConfig(availability_seconds=60),
    )
    cached_provider = CachedRailwayProvider(provider, cache)

    async def request_once():
        return await cached_provider.get_availability(
            "12952",
            "NDLS",
            "MMCT",
            date(2026, 6, 15),
            TravelClass.THIRD_AC,
        )

    snapshots = await asyncio.gather(*(request_once() for _ in range(5)))

    assert len(snapshots) == 5
    assert provider.calls == 1

