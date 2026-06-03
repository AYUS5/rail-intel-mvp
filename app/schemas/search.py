from datetime import date, datetime
from uuid import uuid4

from pydantic import Field, field_validator, model_validator

from app.schemas.common import (
    AvailabilityResponse,
    BaseApiModel,
    CoverageType,
    RouteStopResponse,
    TrainResponse,
    TravelClass,
)


class TrainSearchRequest(BaseApiModel):
    source_station: str = Field(..., min_length=2, max_length=80, examples=["Delhi"])
    destination_station: str = Field(..., min_length=2, max_length=80, examples=["Mumbai"])
    travel_date: date
    travel_class: TravelClass = Field(default=TravelClass.THIRD_AC)
    max_results: int = Field(default=5, ge=1, le=25)
    include_explanations: bool = True

    @field_validator("source_station", "destination_station")
    @classmethod
    def normalize_station_text(cls, value: str) -> str:
        return " ".join(value.upper().split())

    @model_validator(mode="after")
    def source_and_destination_must_differ(self) -> "TrainSearchRequest":
        if self.source_station == self.destination_station:
            raise ValueError("source_station and destination_station must be different")
        return self


class SegmentOpportunityResponse(BaseApiModel):
    train_number: str
    source: RouteStopResponse
    destination: RouteStopResponse
    availability: AvailabilityResponse
    coverage_type: CoverageType
    overlap_ratio: float = Field(..., ge=0, le=1)
    route_mismatch_score: float = Field(..., ge=0)
    confirmation_probability: float = Field(..., ge=0, le=1)
    usefulness_score: float = Field(..., ge=0, le=1)
    distance_km: int = Field(..., ge=0)
    reason_codes: list[str] = Field(default_factory=list)


class RecommendationResponse(BaseApiModel):
    rank: int
    train_number: str
    title: str
    score: float = Field(..., ge=0, le=1)
    confidence: float = Field(..., ge=0, le=1)
    segment: SegmentOpportunityResponse
    explanation: str


class TrainSearchResultResponse(BaseApiModel):
    train: TrainResponse
    route: list[RouteStopResponse]
    direct_availability: AvailabilityResponse
    hidden_segments: list[SegmentOpportunityResponse]
    recommendations: list[RecommendationResponse]
    pairs_considered: int
    explanation: str | None = None


class TrainSearchResponse(BaseApiModel):
    query_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime
    query: TrainSearchRequest
    results: list[TrainSearchResultResponse]
    safety_notice: str = (
        "This platform analyzes availability and route options only. It does not log in to "
        "IRCTC, solve captchas, bypass OTP, or purchase tickets."
    )

