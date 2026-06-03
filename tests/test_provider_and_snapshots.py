from datetime import date

import pytest

from app.repositories.availability_snapshot_repository import (
    InMemoryAvailabilitySnapshotRepository,
)
from app.repositories.fallback_railway_provider import FallbackRailwayProvider
from app.repositories.mock_railway_provider import MockRailwayProvider
from app.repositories.railway_provider import (
    RailwayProviderInterface,
    RailwayProviderUnavailableError,
)
from app.repositories.real_railway_provider import RealRailwayProvider
from app.schemas.common import AvailabilityStatus, TravelClass
from app.services.availability_snapshot_service import AvailabilitySnapshotService
from app.services.dtos import AvailabilitySnapshot


class FailingProvider(RailwayProviderInterface):
    def normalize_station_code(self, station: str) -> str:
        return station.upper()

    async def search_trains(self, *args, **kwargs):
        raise RailwayProviderUnavailableError("upstream down")

    async def get_train_route(self, train_number: str):
        raise RailwayProviderUnavailableError("upstream down")

    async def get_availability(self, *args, **kwargs):
        raise RailwayProviderUnavailableError("upstream down")


class FakeProviderClient:
    async def search_trains(self, *args, **kwargs):
        return {
            "trains": [
                {
                    "number": "12952",
                    "name": "Mumbai Rajdhani Express",
                    "origin_station_code": "NDLS",
                    "destination_station_code": "MMCT",
                    "stops": [
                        {"code": "NDLS", "name": "New Delhi", "sequence": 0, "distance_km": 0},
                        {
                            "code": "MMCT",
                            "name": "Mumbai Central",
                            "sequence": 1,
                            "distance_km": 1384,
                        },
                    ],
                }
            ]
        }

    async def get_train_route(self, *args, **kwargs):
        trains = await self.search_trains()
        return {"train": trains["trains"][0]}

    async def get_availability(self, *args, **kwargs):
        return {
            "availability": {
                "status": "AVL",
                "available_count": 2,
                "source_station_code": "NDLS",
                "destination_station_code": "MMCT",
                "provider": "fake",
            }
        }


@pytest.mark.asyncio
async def test_fallback_provider_uses_mock_when_primary_fails() -> None:
    provider = FallbackRailwayProvider(FailingProvider(), MockRailwayProvider())

    trains = await provider.search_trains(
        "Delhi",
        "Mumbai",
        date(2026, 6, 15),
        TravelClass.THIRD_AC,
    )

    assert trains
    assert trains[0].number == "12952"


@pytest.mark.asyncio
async def test_real_provider_uses_mockable_http_adapter() -> None:
    provider = RealRailwayProvider(FakeProviderClient())

    trains = await provider.search_trains(
        "NDLS",
        "MMCT",
        date(2026, 6, 15),
        TravelClass.THIRD_AC,
    )
    availability = await provider.get_availability(
        "12952",
        "NDLS",
        "MMCT",
        date(2026, 6, 15),
        TravelClass.THIRD_AC,
    )

    assert trains[0].number == "12952"
    assert availability.status == AvailabilityStatus.AVAILABLE
    assert availability.provider == "fake"


@pytest.mark.asyncio
async def test_snapshot_service_persists_and_detects_changes() -> None:
    repository = InMemoryAvailabilitySnapshotRepository()
    service = AvailabilitySnapshotService(repository)

    first = AvailabilitySnapshot(
        train_number="12952",
        source_station_code="NDLS",
        destination_station_code="MMCT",
        travel_date=date(2026, 6, 15),
        travel_class=TravelClass.THIRD_AC,
        status=AvailabilityStatus.WAITLIST,
        waitlist_count=120,
    )
    second = AvailabilitySnapshot(
        train_number="12952",
        source_station_code="NDLS",
        destination_station_code="MMCT",
        travel_date=date(2026, 6, 15),
        travel_class=TravelClass.THIRD_AC,
        status=AvailabilityStatus.RAC,
        rac_count=10,
    )

    first_change = await service.store_snapshot(first)
    second_change = await service.store_snapshot(second)

    assert first_change.meaningful is True
    assert first_change.reason == "first_observation"
    assert second_change.meaningful is True
    assert second_change.reason == "status_changed"
