from fastapi import HTTPException, status

from app.api.mappers import to_train_search_result_response
from app.repositories.monitor_repository import MonitorRecord, MonitorRepository
from app.schemas.common import AvailabilityStatus
from app.schemas.monitor import MonitorCheckResponse, MonitorCreateRequest, MonitorResponse
from app.schemas.search import TrainSearchResultResponse
from app.services.ai.explanation_service import AIExplanationService
from app.services.notification_service import NotificationService
from app.services.recommendation_service import RecommendationService
from app.services.route_analysis_service import RouteAnalysisService


class MonitoringService:
    def __init__(
        self,
        repository: MonitorRepository,
        route_analysis_service: RouteAnalysisService,
        recommendation_service: RecommendationService,
        explanation_service: AIExplanationService,
        notification_service: NotificationService,
    ) -> None:
        self._repository = repository
        self._route_analysis_service = route_analysis_service
        self._recommendation_service = recommendation_service
        self._explanation_service = explanation_service
        self._notification_service = notification_service

    async def create_monitor(self, request: MonitorCreateRequest) -> MonitorResponse:
        record = await self._repository.create(request)
        return self._to_response(record)

    async def list_monitors(self) -> list[MonitorResponse]:
        records = await self._repository.list()
        return [self._to_response(record) for record in records]

    async def get_monitor(self, monitor_id: str) -> MonitorResponse:
        record = await self._repository.get(monitor_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitor not found")
        return self._to_response(record)

    async def delete_monitor(self, monitor_id: str) -> None:
        deleted = await self._repository.delete(monitor_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitor not found")

    async def run_check(self, monitor_id: str) -> MonitorCheckResponse:
        record = await self._repository.get(monitor_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitor not found")

        results = await self._analyze_monitor(record)
        matched_results = [result for result in results if self._result_matches_threshold(record, result)]
        updated = await self._repository.update_check_result(record.id, results)
        if matched_results:
            await self._notification_service.send_availability_alert(record, matched_results)
        return MonitorCheckResponse(
            monitor=self._to_response(updated or record),
            alert_triggered=bool(matched_results),
            matched_results=matched_results,
        )

    async def _analyze_monitor(self, record: MonitorRecord) -> list[TrainSearchResultResponse]:
        request = record.request
        analyses = await self._route_analysis_service.analyze_search(
            request.source_station,
            request.destination_station,
            request.travel_date,
            request.travel_class,
            max_results=25,
        )
        if request.train_number:
            analyses = [analysis for analysis in analyses if analysis.train.number == request.train_number]

        results: list[TrainSearchResultResponse] = []
        for analysis in analyses:
            recommendations = self._recommendation_service.rank_train_recommendations(analysis)
            explanation = await self._explanation_service.explain_train(
                self._monitor_to_search_request(record),
                analysis,
                recommendations,
            )
            results.append(to_train_search_result_response(analysis, recommendations, explanation))
        return results

    def _result_matches_threshold(
        self,
        record: MonitorRecord,
        result: TrainSearchResultResponse,
    ) -> bool:
        threshold = record.request.threshold_status
        statuses = [result.direct_availability.status]
        statuses.extend(segment.availability.status for segment in result.hidden_segments[:3])
        if threshold == AvailabilityStatus.AVAILABLE:
            return AvailabilityStatus.AVAILABLE in statuses
        if threshold == AvailabilityStatus.RAC:
            return AvailabilityStatus.AVAILABLE in statuses or AvailabilityStatus.RAC in statuses
        return any(status != AvailabilityStatus.UNKNOWN for status in statuses)

    def _monitor_to_search_request(self, record: MonitorRecord):
        from app.schemas.search import TrainSearchRequest

        return TrainSearchRequest(
            source_station=record.request.source_station,
            destination_station=record.request.destination_station,
            travel_date=record.request.travel_date,
            travel_class=record.request.travel_class,
            max_results=25,
            include_explanations=True,
        )

    def _to_response(self, record: MonitorRecord) -> MonitorResponse:
        request = record.request
        return MonitorResponse(
            id=record.id,
            source_station=request.source_station,
            destination_station=request.destination_station,
            travel_date=request.travel_date,
            travel_class=request.travel_class,
            train_number=request.train_number,
            threshold_status=request.threshold_status,
            notification_target=request.notification_target,
            is_active=record.is_active,
            created_at=record.created_at,
            last_checked_at=record.last_checked_at,
            last_results=record.last_results,
        )

