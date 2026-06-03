import logging
from datetime import date

from app.repositories.railway_provider import RailwayProviderError, RailwayProviderInterface
from app.schemas.common import TravelClass
from app.services.dtos import AvailabilitySnapshot, TrainRoute
from app.utils.request_context import get_request_id

logger = logging.getLogger(__name__)


class FallbackRailwayProvider(RailwayProviderInterface):
    """Provider decorator that falls back when the primary upstream fails.

    This keeps business services isolated from network instability and lets local/dev
    deployments use the mock provider as a graceful degraded mode.
    """

    def __init__(
        self,
        primary: RailwayProviderInterface,
        fallback: RailwayProviderInterface,
    ) -> None:
        self._primary = primary
        self._fallback = fallback

    def normalize_station_code(self, station: str) -> str:
        try:
            return self._primary.normalize_station_code(station)
        except Exception:
            return self._fallback.normalize_station_code(station)

    async def search_trains(
        self,
        source_station: str,
        destination_station: str,
        travel_date: date,
        travel_class: TravelClass,
    ) -> list[TrainRoute]:
        try:
            return await self._primary.search_trains(
                source_station,
                destination_station,
                travel_date,
                travel_class,
            )
        except RailwayProviderError as exc:
            logger.warning(
                "provider_fallback_search",
                extra={"error": str(exc), "request_id": get_request_id()},
            )
            return await self._fallback.search_trains(
                source_station,
                destination_station,
                travel_date,
                travel_class,
            )

    async def get_train_route(self, train_number: str) -> TrainRoute | None:
        try:
            return await self._primary.get_train_route(train_number)
        except RailwayProviderError as exc:
            logger.warning(
                "provider_fallback_route",
                extra={
                    "train_number": train_number,
                    "error": str(exc),
                    "request_id": get_request_id(),
                },
            )
            return await self._fallback.get_train_route(train_number)

    async def get_availability(
        self,
        train_number: str,
        source_station: str,
        destination_station: str,
        travel_date: date,
        travel_class: TravelClass,
    ) -> AvailabilitySnapshot:
        try:
            return await self._primary.get_availability(
                train_number,
                source_station,
                destination_station,
                travel_date,
                travel_class,
            )
        except RailwayProviderError as exc:
            logger.warning(
                "provider_fallback_availability",
                extra={
                    "train_number": train_number,
                    "source_station": source_station,
                    "destination_station": destination_station,
                    "error": str(exc),
                    "request_id": get_request_id(),
                },
            )
            return await self._fallback.get_availability(
                train_number,
                source_station,
                destination_station,
                travel_date,
                travel_class,
            )
