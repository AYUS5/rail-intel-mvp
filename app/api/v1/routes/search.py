from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.api.deps import (
    get_explanation_service,
    get_recommendation_service,
    get_route_analysis_service,
)
from app.api.mappers import to_train_search_result_response
from app.schemas.search import TrainSearchRequest, TrainSearchResponse
from app.services.ai.explanation_service import AIExplanationService
from app.services.recommendation_service import RecommendationService
from app.services.route_analysis_service import RouteAnalysisService

router = APIRouter()


@router.post("/trains", response_model=TrainSearchResponse)
async def search_trains(
    request: TrainSearchRequest,
    route_analysis_service: RouteAnalysisService = Depends(get_route_analysis_service),
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
    explanation_service: AIExplanationService = Depends(get_explanation_service),
) -> TrainSearchResponse:
    analyses = await route_analysis_service.analyze_search(
        request.source_station,
        request.destination_station,
        request.travel_date,
        request.travel_class,
        request.max_results,
    )

    results = []
    for analysis in analyses:
        recommendations = recommendation_service.rank_train_recommendations(analysis)
        explanation = None
        if request.include_explanations:
            explanation = await explanation_service.explain_train(request, analysis, recommendations)
        results.append(to_train_search_result_response(analysis, recommendations, explanation))

    return TrainSearchResponse(
        generated_at=datetime.now(timezone.utc),
        query=request,
        results=results,
    )


@router.post("/hidden-segments", response_model=TrainSearchResponse)
async def detect_hidden_segments(
    request: TrainSearchRequest,
    route_analysis_service: RouteAnalysisService = Depends(get_route_analysis_service),
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
    explanation_service: AIExplanationService = Depends(get_explanation_service),
) -> TrainSearchResponse:
    return await search_trains(
        request,
        route_analysis_service,
        recommendation_service,
        explanation_service,
    )

