from __future__ import annotations

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import redis.asyncio as redis

from app.utils.request_context import get_request_id

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CacheTTLConfig:
    train_route_seconds: int = 60 * 60 * 24
    availability_seconds: int = 60
    station_metadata_seconds: int = 60 * 60 * 24 * 7


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    sets: int = 0
    errors: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0


class CacheBackend(ABC):
    @abstractmethod
    async def get_json(self, key: str) -> dict[str, Any] | list[Any] | None:
        raise NotImplementedError

    @abstractmethod
    async def set_json(self, key: str, value: dict[str, Any] | list[Any], ttl_seconds: int) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, key: str) -> None:
        raise NotImplementedError


class InMemoryCacheBackend(CacheBackend):
    def __init__(self) -> None:
        self._values: dict[str, tuple[float, dict[str, Any] | list[Any]]] = {}

    async def get_json(self, key: str) -> dict[str, Any] | list[Any] | None:
        item = self._values.get(key)
        if item is None:
            return None
        expires_at, value = item
        if expires_at < time.time():
            self._values.pop(key, None)
            return None
        return value

    async def set_json(self, key: str, value: dict[str, Any] | list[Any], ttl_seconds: int) -> None:
        self._values[key] = (time.time() + ttl_seconds, value)

    async def delete(self, key: str) -> None:
        self._values.pop(key, None)


class RedisCacheBackend(CacheBackend):
    def __init__(self, redis_url: str) -> None:
        self._client = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)

    async def get_json(self, key: str) -> dict[str, Any] | list[Any] | None:
        value = await self._client.get(key)
        if value is None:
            return None
        decoded = json.loads(value)
        if not isinstance(decoded, dict | list):
            return None
        return decoded

    async def set_json(self, key: str, value: dict[str, Any] | list[Any], ttl_seconds: int) -> None:
        await self._client.set(key, json.dumps(value), ex=ttl_seconds)

    async def delete(self, key: str) -> None:
        await self._client.delete(key)


class CacheKeyBuilder:
    prefix = "railintel:v1"

    @classmethod
    def train_route(cls, train_number: str) -> str:
        return f"{cls.prefix}:route:{train_number}"

    @classmethod
    def availability(
        cls,
        train_number: str,
        source_station: str,
        destination_station: str,
        travel_date: str,
        travel_class: str,
    ) -> str:
        return (
            f"{cls.prefix}:availability:{train_number}:{source_station}:"
            f"{destination_station}:{travel_date}:{travel_class}"
        )

    @classmethod
    def station_metadata(cls, station_code: str) -> str:
        return f"{cls.prefix}:station:{station_code}"

    @classmethod
    def train_search(
        cls,
        source_station: str,
        destination_station: str,
        travel_date: str,
        travel_class: str,
    ) -> str:
        return (
            f"{cls.prefix}:search:{source_station}:{destination_station}:"
            f"{travel_date}:{travel_class}"
        )


class SingleFlight:
    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = {}
        self._guard = asyncio.Lock()

    async def lock_for(self, key: str) -> asyncio.Lock:
        async with self._guard:
            lock = self._locks.get(key)
            if lock is None:
                lock = asyncio.Lock()
                self._locks[key] = lock
            return lock


class CacheService:
    def __init__(self, backend: CacheBackend, ttl: CacheTTLConfig | None = None) -> None:
        self._backend = backend
        self._ttl = ttl or CacheTTLConfig()
        self._singleflight = SingleFlight()
        self._stats = CacheStats()

    @property
    def ttl(self) -> CacheTTLConfig:
        return self._ttl

    @property
    def stats(self) -> CacheStats:
        return self._stats

    async def get_json(self, key: str) -> dict[str, Any] | list[Any] | None:
        try:
            value = await self._backend.get_json(key)
            if value is None:
                self._stats.misses += 1
            else:
                self._stats.hits += 1
            logger.info(
                "cache_%s",
                "hit" if value is not None else "miss",
                extra={
                    "cache_key": key,
                    "cache_hit_rate": round(self._stats.hit_rate, 4),
                    "request_id": get_request_id(),
                },
            )
            return value
        except Exception as exc:
            self._stats.errors += 1
            logger.warning(
                "cache_read_error",
                extra={"cache_key": key, "error": str(exc), "request_id": get_request_id()},
            )
            return None

    async def set_json(
        self,
        key: str,
        value: dict[str, Any] | list[Any],
        ttl_seconds: int,
    ) -> None:
        try:
            await self._backend.set_json(key, value, ttl_seconds)
            self._stats.sets += 1
            logger.info(
                "cache_set",
                extra={
                    "cache_key": key,
                    "ttl_seconds": ttl_seconds,
                    "request_id": get_request_id(),
                },
            )
        except Exception as exc:
            self._stats.errors += 1
            logger.warning(
                "cache_write_error",
                extra={"cache_key": key, "error": str(exc), "request_id": get_request_id()},
            )

    async def delete(self, key: str) -> None:
        await self._backend.delete(key)

    async def lock_for(self, key: str) -> asyncio.Lock:
        return await self._singleflight.lock_for(key)
