from app.schemas.common import AvailabilityResponse, RouteStopResponse, TrainResponse
from app.schemas.search import (
    RecommendationResponse,
    SegmentOpportunityResponse,
    TrainSearchResultResponse,
)
from app.services.dtos import (
    AvailabilitySnapshot,
    RecommendationCandidate,
    SegmentOpportunity,
    StationStop,
    TrainAnalysis,
    TrainRoute,
)


def to_route_stop_response(stop: StationStop) -> RouteStopResponse:
    return RouteStopResponse(
        code=stop.code,
        name=stop.name,
        sequence=stop.sequence,
        distance_km=stop.distance_km,
        arrival=stop.arrival,
        departure=stop.departure,
    )


def to_train_response(train: TrainRoute) -> TrainResponse:
    return TrainResponse(
        number=train.number,
        name=train.name,
        origin_station_code=train.origin_station_code,
        destination_station_code=train.destination_station_code,
    )


def to_availability_response(availability: AvailabilitySnapshot) -> AvailabilityResponse:
    return AvailabilityResponse(
        status=availability.status,
        available_count=availability.available_count,
        rac_count=availability.rac_count,
        waitlist_count=availability.waitlist_count,
        source_station_code=availability.source_station_code,
        destination_station_code=availability.destination_station_code,
        checked_at=availability.checked_at,
        provider=availability.provider,
    )


def to_segment_response(segment: SegmentOpportunity) -> SegmentOpportunityResponse:
    return SegmentOpportunityResponse(
        train_number=segment.train_number,
        source=to_route_stop_response(segment.source),
        destination=to_route_stop_response(segment.destination),
        availability=to_availability_response(segment.availability),
        coverage_type=segment.coverage_type,
        overlap_ratio=segment.overlap_ratio,
        route_mismatch_score=segment.route_mismatch_score,
        confirmation_probability=segment.confirmation_probability,
        usefulness_score=segment.usefulness_score,
        distance_km=segment.distance_km,
        reason_codes=list(segment.reason_codes),
    )


def to_recommendation_response(recommendation: RecommendationCandidate) -> RecommendationResponse:
    return RecommendationResponse(
        rank=recommendation.rank,
        train_number=recommendation.train_number,
        title=recommendation.title,
        score=recommendation.score,
        confidence=recommendation.confidence,
        segment=to_segment_response(recommendation.segment),
        explanation=recommendation.explanation,
    )


def to_train_search_result_response(
    analysis: TrainAnalysis,
    recommendations: list[RecommendationCandidate],
    explanation: str | None,
) -> TrainSearchResultResponse:
    return TrainSearchResultResponse(
        train=to_train_response(analysis.train),
        route=[to_route_stop_response(stop) for stop in analysis.train.stops],
        direct_availability=to_availability_response(analysis.direct_availability),
        hidden_segments=[to_segment_response(segment) for segment in analysis.hidden_segments],
        recommendations=[to_recommendation_response(item) for item in recommendations],
        pairs_considered=analysis.pairs_considered,
        explanation=explanation,
    )

