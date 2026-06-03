from datetime import date

from app.schemas.common import AvailabilityStatus, TravelClass
from app.services.dtos import AvailabilitySnapshot
from app.utils.scoring import availability_quality, estimate_confirmation_probability


def test_available_status_scores_higher_than_waitlist() -> None:
    available = AvailabilitySnapshot(
        train_number="12952",
        source_station_code="MTJ",
        destination_station_code="MMCT",
        travel_date=date(2026, 6, 15),
        travel_class=TravelClass.THIRD_AC,
        status=AvailabilityStatus.AVAILABLE,
        available_count=9,
    )
    waitlist = AvailabilitySnapshot(
        train_number="12952",
        source_station_code="NDLS",
        destination_station_code="MMCT",
        travel_date=date(2026, 6, 15),
        travel_class=TravelClass.THIRD_AC,
        status=AvailabilityStatus.WAITLIST,
        waitlist_count=120,
    )

    assert availability_quality(available) > availability_quality(waitlist)
    assert estimate_confirmation_probability(available) > estimate_confirmation_probability(waitlist)

