from datetime import date

from app.repositories.railway_provider import RailwayProviderInterface
from app.schemas.common import TravelClass
from app.services.dtos import AvailabilitySnapshot, TrainRoute


class RailwayService:
    def __init__(self, provider: RailwayProviderInterface) -> None:
        self._provider = provider

    def normalize_station_code(self, station: str) -> str:
        return self._provider.normalize_station_code(station)

    async def search_trains(
        self,
        source_station: str,
        destination_station: str,
        travel_date: date,
        travel_class: TravelClass,
    ) -> list[TrainRoute]:
        return await self._provider.search_trains(
            source_station,
            destination_station,
            travel_date,
            travel_class,
        )

    async def get_availability(
        self,
        train_number: str,
        source_station: str,
        destination_station: str,
        travel_date: date,
        travel_class: TravelClass,
    ) -> AvailabilitySnapshot:
        return await self._provider.get_availability(
            train_number,
            source_station,
            destination_station,
            travel_date,
            travel_class,
        )

    async def get_route(self, train_number: str) -> TrainRoute | None:
        return await self._provider.get_train_route(train_number)
