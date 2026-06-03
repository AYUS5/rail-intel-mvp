import logging
from datetime import date

from app.repositories.railway_provider import RailwayProviderInterface
from app.schemas.common import TravelClass
from app.services.cache_service import CacheKeyBuilder, CacheService
from app.services.dtos import AvailabilitySnapshot, TrainRoute
from app.utils.serialization import (
    availability_from_dict,
    availability_to_dict,
    station_stop_to_dict,
    train_route_from_dict,
    train_route_to_dict,
)

logger = logging.getLogger(__name__)


class CachedRailwayProvider(RailwayProviderInterface):
    def __init__(
        self,
        provider: RailwayProviderInterface,
        cache_service: CacheService,
    ) -> None:
        self._provider = provider
        self._cache = cache_service

    def normalize_station_code(self, station: str) -> str:
        return self._provider.normalize_station_code(station)

    async def search_trains(
        self,
        source_station: str,
        destination_station: str,
        travel_date: date,
        travel_class: TravelClass,
    ) -> list[TrainRoute]:
        source_code = self.normalize_station_code(source_station)
        destination_code = self.normalize_station_code(destination_station)
        key = CacheKeyBuilder.train_search(
            source_code,
            destination_code,
            travel_date.isoformat(),
            travel_class.value,
        )
        cached = await self._cache.get_json(key)
        if isinstance(cached, list):
            return [train_route_from_dict(item) for item in cached if isinstance(item, dict)]

        lock = await self._cache.lock_for(key)
        async with lock:
            cached = await self._cache.get_json(key)
            if isinstance(cached, list):
                return [train_route_from_dict(item) for item in cached if isinstance(item, dict)]

            routes = await self._provider.search_trains(
                source_code,
                destination_code,
                travel_date,
                travel_class,
            )
            await self._cache.set_json(
                key,
                [train_route_to_dict(route) for route in routes],
                ttl_seconds=self._cache.ttl.train_route_seconds,
            )
            for route in routes:
                await self._cache_train_route(route)
            return routes

    async def get_train_route(self, train_number: str) -> TrainRoute | None:
        key = CacheKeyBuilder.train_route(train_number)
        cached = await self._cache.get_json(key)
        if isinstance(cached, dict):
            return train_route_from_dict(cached)

        lock = await self._cache.lock_for(key)
        async with lock:
            cached = await self._cache.get_json(key)
            if isinstance(cached, dict):
                return train_route_from_dict(cached)

            route = await self._provider.get_train_route(train_number)
            if route is not None:
                await self._cache_train_route(route)
            return route

    async def get_availability(
        self,
        train_number: str,
        source_station: str,
        destination_station: str,
        travel_date: date,
        travel_class: TravelClass,
    ) -> AvailabilitySnapshot:
        source_code = self.normalize_station_code(source_station)
        destination_code = self.normalize_station_code(destination_station)
        key = CacheKeyBuilder.availability(
            train_number,
            source_code,
            destination_code,
            travel_date.isoformat(),
            travel_class.value,
        )
        cached = await self._cache.get_json(key)
        if isinstance(cached, dict):
            return availability_from_dict(cached)

        lock = await self._cache.lock_for(key)
        async with lock:
            cached = await self._cache.get_json(key)
            if isinstance(cached, dict):
                return availability_from_dict(cached)

            snapshot = await self._provider.get_availability(
                train_number,
                source_code,
                destination_code,
                travel_date,
                travel_class,
            )
            await self._cache.set_json(
                key,
                availability_to_dict(snapshot),
                ttl_seconds=self._cache.ttl.availability_seconds,
            )
            return snapshot

    async def invalidate_availability(
        self,
        train_number: str,
        source_station: str,
        destination_station: str,
        travel_date: date,
        travel_class: TravelClass,
    ) -> None:
        key = CacheKeyBuilder.availability(
            train_number,
            self.normalize_station_code(source_station),
            self.normalize_station_code(destination_station),
            travel_date.isoformat(),
            travel_class.value,
        )
        await self._cache.delete(key)

    async def _cache_train_route(self, route: TrainRoute) -> None:
        await self._cache.set_json(
            CacheKeyBuilder.train_route(route.number),
            train_route_to_dict(route),
            ttl_seconds=self._cache.ttl.train_route_seconds,
        )
        for stop in route.stops:
            await self._cache.set_json(
                CacheKeyBuilder.station_metadata(stop.code),
                station_stop_to_dict(stop),
                ttl_seconds=self._cache.ttl.station_metadata_seconds,
            )

