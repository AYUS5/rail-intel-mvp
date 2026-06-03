from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from app.api_client.http import AsyncHttpClient
from app.schemas.common import TravelClass


@dataclass(frozen=True)
class RailwayProviderClientConfig:
    api_key: str = ""
    search_path: str = "/TrainBetweenStation/apikey/{api_key}/From/{source}/To/{destination}"
    route_path_template: str = "/TrainSchedule/apikey/{api_key}/TrainNumber/{train_number}"
    availability_path: str = "/SeatAvailability/apikey/{api_key}/TrainNumber/{train_number}/From/{source}/To/{destination}/Date/{date}/Quota/GN/Class/{class_code}"


class RailwayProviderClient:
    def __init__(
        self,
        http_client: AsyncHttpClient,
        config: RailwayProviderClientConfig | None = None,
    ) -> None:
        self._http_client = http_client
        self._config = config or RailwayProviderClientConfig()

    async def search_trains(
        self,
        source_station: str,
        destination_station: str,
        travel_date: date,
        travel_class: TravelClass,
    ) -> dict[str, Any]:
        path = self._config.search_path.format(
            api_key=self._config.api_key,
            source=source_station,
            destination=destination_station,
        )
        return await self._http_client.get_json(path, params={})

    async def get_train_route(self, train_number: str) -> dict[str, Any]:
        path = self._config.route_path_template.format(
            api_key=self._config.api_key,
            train_number=train_number,
        )
        payload = await self._http_client.get_json(path, params={})
        # inject train_number since indianrailapi.com doesn't return it in the body
        payload["_train_number"] = train_number
        return payload

    async def get_availability(
        self,
        train_number: str,
        source_station: str,
        destination_station: str,
        travel_date: date,
        travel_class: TravelClass,
    ) -> dict[str, Any]:
        path = self._config.availability_path.format(
            api_key=self._config.api_key,
            train_number=train_number,
            source=source_station,
            destination=destination_station,
            date=travel_date.strftime("%Y%m%d"),
            class_code=self._map_class(travel_class),
        )
        return await self._http_client.get_json(path, params={})

    def _map_class(self, travel_class: TravelClass) -> str:
        return {
            TravelClass.FIRST_AC: "1A",
            TravelClass.SECOND_AC: "2A",
            TravelClass.THIRD_AC: "3A",
            TravelClass.SLEEPER: "SL",
            TravelClass.CHAIR_CAR: "CC",
        }.get(travel_class, "3A")