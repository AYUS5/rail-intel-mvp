from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from app.schemas.common import AvailabilityStatus, CoverageType, TravelClass


@dataclass(frozen=True)
class StationStop:
    code: str
    name: str
    sequence: int
    distance_km: int
    arrival: str | None = None
    departure: str | None = None


@dataclass(frozen=True)
class TrainRoute:
    number: str
    name: str
    origin_station_code: str
    destination_station_code: str
    stops: tuple[StationStop, ...]

    def index_by_station_code(self) -> dict[str, int]:
        return {stop.code: index for index, stop in enumerate(self.stops)}


@dataclass(frozen=True)
class AvailabilitySnapshot:
    train_number: str
    source_station_code: str
    destination_station_code: str
    travel_date: date
    travel_class: TravelClass
    status: AvailabilityStatus
    available_count: int | None = None
    rac_count: int | None = None
    waitlist_count: int | None = None
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    provider: str = "mock"


@dataclass(frozen=True)
class SegmentOpportunity:
    train_number: str
    source: StationStop
    destination: StationStop
    availability: AvailabilitySnapshot
    coverage_type: CoverageType
    overlap_ratio: float
    route_mismatch_score: float
    confirmation_probability: float
    usefulness_score: float
    distance_km: int
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class TrainAnalysis:
    train: TrainRoute
    direct_availability: AvailabilitySnapshot
    hidden_segments: tuple[SegmentOpportunity, ...]
    pairs_considered: int


@dataclass(frozen=True)
class RecommendationCandidate:
    rank: int
    train_number: str
    title: str
    score: float
    confidence: float
    segment: SegmentOpportunity
    explanation: str

