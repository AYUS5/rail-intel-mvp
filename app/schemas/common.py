from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class TravelClass(StrEnum):
    SL = "SL"
    THIRD_AC = "3AC"
    SECOND_AC = "2AC"
    FIRST_AC = "1AC"
    CC = "CC"
    EC = "EC"


class AvailabilityStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    RAC = "RAC"
    WAITLIST = "WAITLIST"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    UNKNOWN = "UNKNOWN"


class CoverageType(StrEnum):
    FULL_COVERAGE = "FULL_COVERAGE"
    EXTENDED_COVERAGE = "EXTENDED_COVERAGE"
    SAME_BOARDING_PARTIAL = "SAME_BOARDING_PARTIAL"
    LATER_BOARDING_TO_DESTINATION = "LATER_BOARDING_TO_DESTINATION"
    INTERMEDIATE_SEGMENT = "INTERMEDIATE_SEGMENT"


class RouteStopResponse(BaseModel):
    code: str
    name: str
    sequence: int
    distance_km: int
    arrival: str | None = None
    departure: str | None = None


class TrainResponse(BaseModel):
    number: str
    name: str
    origin_station_code: str
    destination_station_code: str


class AvailabilityResponse(BaseModel):
    status: AvailabilityStatus
    available_count: int | None = Field(default=None, ge=0)
    rac_count: int | None = Field(default=None, ge=0)
    waitlist_count: int | None = Field(default=None, ge=0)
    source_station_code: str
    destination_station_code: str
    checked_at: datetime
    provider: str = "mock"


class ErrorResponse(BaseModel):
    detail: str


class BaseApiModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

