from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime

from app.schemas.common import AvailabilityStatus, TravelClass


@dataclass(frozen=True)
class PredictionContext:
    train_number: str
    source_station_code: str
    destination_station_code: str
    travel_date: date
    travel_class: TravelClass
    observed_at: datetime
    current_status: AvailabilityStatus
    available_count: int | None
    rac_count: int | None
    waitlist_count: int | None


@dataclass(frozen=True)
class ConfirmationPrediction:
    probability: float
    confidence: float
    model_name: str
    factors: dict[str, float | str | int | None]


@dataclass(frozen=True)
class WaitlistMovementEstimate:
    expected_movement: int
    confidence: float
    model_name: str
    factors: dict[str, float | str | int | None]


@dataclass(frozen=True)
class QuotaBehaviorSignal:
    quota_name: str
    signal_strength: float
    explanation: str


@dataclass(frozen=True)
class SeasonalTrendSignal:
    period_name: str
    trend_strength: float
    expected_demand_level: str
    explanation: str


class ConfirmationProbabilityPredictor(ABC):
    @abstractmethod
    async def predict_confirmation(
        self,
        context: PredictionContext,
    ) -> ConfirmationPrediction:
        raise NotImplementedError


class WaitlistMovementModel(ABC):
    @abstractmethod
    async def estimate_movement(
        self,
        context: PredictionContext,
    ) -> WaitlistMovementEstimate:
        raise NotImplementedError


class QuotaBehaviorAnalyzer(ABC):
    @abstractmethod
    async def analyze_quota_behavior(
        self,
        context: PredictionContext,
    ) -> list[QuotaBehaviorSignal]:
        raise NotImplementedError


class SeasonalTrendAnalyzer(ABC):
    @abstractmethod
    async def analyze_seasonality(
        self,
        context: PredictionContext,
    ) -> list[SeasonalTrendSignal]:
        raise NotImplementedError
