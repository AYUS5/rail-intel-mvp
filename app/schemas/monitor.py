from datetime import date, datetime
from uuid import uuid4

from pydantic import Field, field_validator, model_validator

from app.schemas.common import AvailabilityStatus, BaseApiModel, TravelClass
from app.schemas.search import TrainSearchResultResponse


class MonitorCreateRequest(BaseApiModel):
    source_station: str = Field(..., min_length=2, max_length=80)
    destination_station: str = Field(..., min_length=2, max_length=80)
    travel_date: date
    travel_class: TravelClass
    train_number: str | None = Field(default=None, min_length=3, max_length=12)
    threshold_status: AvailabilityStatus = AvailabilityStatus.RAC
    notification_target: str | None = Field(
        default=None,
        description="Email, webhook URL, or user channel identifier. Delivery is pluggable.",
    )

    @field_validator("source_station", "destination_station", "train_number")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return " ".join(value.upper().split())

    @model_validator(mode="after")
    def source_and_destination_must_differ(self) -> "MonitorCreateRequest":
        if self.source_station == self.destination_station:
            raise ValueError("source_station and destination_station must be different")
        return self


class MonitorResponse(BaseApiModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    source_station: str
    destination_station: str
    travel_date: date
    travel_class: TravelClass
    train_number: str | None = None
    threshold_status: AvailabilityStatus
    notification_target: str | None = None
    is_active: bool
    created_at: datetime
    last_checked_at: datetime | None = None
    last_results: list[TrainSearchResultResponse] = Field(default_factory=list)


class MonitorCheckResponse(BaseApiModel):
    monitor: MonitorResponse
    alert_triggered: bool
    matched_results: list[TrainSearchResultResponse]

