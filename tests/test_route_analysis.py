from datetime import date

import pytest

from app.repositories.mock_railway_provider import MockRailwayDataProvider
from app.schemas.common import AvailabilityStatus, TravelClass
from app.services.railway_service import RailwayService
from app.services.route_analysis_service import RouteAnalysisConfig, RouteAnalysisService


@pytest.mark.asyncio
async def test_hidden_segments_are_detected_for_waitlisted_direct_route() -> None:
    provider = MockRailwayDataProvider()
    railway_service = RailwayService(provider)
    analysis_service = RouteAnalysisService(
        railway_service,
        RouteAnalysisConfig(
            max_station_extension=2,
            min_overlap_ratio=0.25,
            max_candidates_per_train=10,
        ),
    )

    analyses = await analysis_service.analyze_search(
        "Delhi",
        "Mumbai",
        date(2026, 6, 15),
        TravelClass.THIRD_AC,
        max_results=5,
    )

    assert len(analyses) == 1
    analysis = analyses[0]
    assert analysis.train.number == "12952"
    assert analysis.direct_availability.status == AvailabilityStatus.WAITLIST
    assert analysis.direct_availability.waitlist_count == 120

    segment_map = {
        (segment.source.code, segment.destination.code): segment
        for segment in analysis.hidden_segments
    }
    assert ("MTJ", "MMCT") in segment_map
    assert ("NDLS", "KOTA") in segment_map
    assert segment_map[("MTJ", "MMCT")].availability.status == AvailabilityStatus.AVAILABLE
    assert segment_map[("NDLS", "KOTA")].availability.status == AvailabilityStatus.AVAILABLE


@pytest.mark.asyncio
async def test_candidates_are_sorted_by_usefulness() -> None:
    provider = MockRailwayDataProvider()
    service = RouteAnalysisService(RailwayService(provider))

    analyses = await service.analyze_search(
        "NDLS",
        "MMCT",
        date(2026, 6, 15),
        TravelClass.THIRD_AC,
        max_results=1,
    )

    scores = [segment.usefulness_score for segment in analyses[0].hidden_segments]
    assert scores == sorted(scores, reverse=True)
    assert analyses[0].pairs_considered > 0

