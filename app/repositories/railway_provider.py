from abc import ABC, abstractmethod
from datetime import date

from app.schemas.common import TravelClass
from app.services.dtos import AvailabilitySnapshot, TrainRoute


class RailwayProviderError(RuntimeError):
    """Base exception for provider-side failures."""


class RailwayProviderTimeoutError(RailwayProviderError):
    """Raised when an upstream provider exceeds the configured timeout."""


class RailwayProviderUnavailableError(RailwayProviderError):
    """Raised when an upstream provider is temporarily unavailable."""


class RailwayProviderInterface(ABC):
    """Provider boundary for approved railway data sources.

    Implementations must respect railway platform terms and should use sanctioned APIs,
    cached datasets, partner feeds, or manual imports. This boundary must not perform
    captcha solving, credential automation, OTP bypassing, or ticket purchasing.
    """

    @abstractmethod
    def normalize_station_code(self, station: str) -> str:
        raise NotImplementedError

    @abstractmethod
    async def search_trains(
        self,
        source_station: str,
        destination_station: str,
        travel_date: date,
        travel_class: TravelClass,
    ) -> list[TrainRoute]:
        raise NotImplementedError

    @abstractmethod
    async def get_train_route(self, train_number: str) -> TrainRoute | None:
        raise NotImplementedError

    async def get_route(self, train_number: str) -> TrainRoute | None:
        """Backward-compatible alias for older service code."""

        return await self.get_train_route(train_number)

    @abstractmethod
    async def get_availability(
        self,
        train_number: str,
        source_station: str,
        destination_station: str,
        travel_date: date,
        travel_class: TravelClass,
    ) -> AvailabilitySnapshot:
        raise NotImplementedError


RailwayDataProvider = RailwayProviderInterface
