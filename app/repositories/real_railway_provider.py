import logging
import time
from datetime import date

from app.adapters.railway_response_adapter import RailwayResponseAdapter
from app.api_client.errors import (
    ApiClientError,
    ApiClientHTTPStatusError,
    ApiClientTimeoutError,
)
from app.provider_clients.railway_api_client import RailwayProviderClient
from app.repositories.railway_provider import (
    RailwayProviderInterface,
    RailwayProviderTimeoutError,
    RailwayProviderUnavailableError,
)
from app.schemas.common import TravelClass
from app.services.dtos import AvailabilitySnapshot, TrainRoute
from app.utils.request_context import get_request_id

logger = logging.getLogger(__name__)


class RealRailwayProvider(RailwayProviderInterface):
    """Production-style provider backed by an external railway API client.

    Vendor-specific endpoint details stay in provider clients. Payload normalization
    stays in adapters. Business services receive only internal DTOs.
    """

    def __init__(
        self,
        provider_client: RailwayProviderClient,
        response_adapter: RailwayResponseAdapter | None = None,
    ) -> None:
        self._provider_client = provider_client
        self._adapter = response_adapter or RailwayResponseAdapter()

    def normalize_station_code(self, station: str) -> str:
        return self._adapter.normalize_station_code(station)

    async def search_trains(
        self,
        source_station: str,
        destination_station: str,
        travel_date: date,
        travel_class: TravelClass,
    ) -> list[TrainRoute]:
        start = time.perf_counter()
        try:
            payload = await self._provider_client.search_trains(
                self.normalize_station_code(source_station),
                self.normalize_station_code(destination_station),
                travel_date,
                travel_class,
            )
            trains = self._adapter.parse_train_search(payload)
            logger.info(
                "real_provider_search_complete",
                extra={
                    "source_station": source_station,
                    "destination_station": destination_station,
                    "travel_class": travel_class.value,
                    "train_count": len(trains),
                    "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                    "request_id": get_request_id(),
                },
            )
            return trains
        except ApiClientError as exc:
            self._raise_provider_error("search_trains", exc)

    async def get_train_route(self, train_number: str) -> TrainRoute | None:
        start = time.perf_counter()
        try:
            payload = await self._provider_client.get_train_route(train_number)
            route = self._adapter.parse_train_route_response(payload)
            logger.info(
                "real_provider_route_complete",
                extra={
                    "train_number": train_number,
                    "has_route": route is not None,
                    "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                    "request_id": get_request_id(),
                },
            )
            return route
        except ApiClientError as exc:
            self._raise_provider_error("get_train_route", exc)

    async def get_availability(
        self,
        train_number: str,
        source_station: str,
        destination_station: str,
        travel_date: date,
        travel_class: TravelClass,
    ) -> AvailabilitySnapshot:
        start = time.perf_counter()
        try:
            payload = await self._provider_client.get_availability(
                train_number,
                self.normalize_station_code(source_station),
                self.normalize_station_code(destination_station),
                travel_date,
                travel_class,
            )
            snapshot = self._adapter.parse_availability(
                payload,
                train_number,
                source_station,
                destination_station,
                travel_date,
                travel_class,
            )
            logger.info(
                "real_provider_availability_complete",
                extra={
                    "train_number": train_number,
                    "source_station": source_station,
                    "destination_station": destination_station,
                    "status": snapshot.status.value,
                    "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                    "request_id": get_request_id(),
                },
            )
            return snapshot
        except ApiClientError as exc:
            self._raise_provider_error("get_availability", exc)

    def _raise_provider_error(self, operation: str, exc: ApiClientError):
        logger.warning(
            "real_provider_operation_failed",
            extra={"operation": operation, "error": str(exc), "request_id": get_request_id()},
        )
        if isinstance(exc, ApiClientTimeoutError):
            raise RailwayProviderTimeoutError(f"{operation} timed out") from exc
        if isinstance(exc, ApiClientHTTPStatusError):
            raise RailwayProviderUnavailableError(
                f"{operation} failed with HTTP {exc.status_code}"
            ) from exc
        raise RailwayProviderUnavailableError(f"{operation} failed") from exc
