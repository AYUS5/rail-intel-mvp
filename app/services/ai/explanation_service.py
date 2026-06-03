from app.schemas.common import AvailabilityStatus
from app.schemas.search import TrainSearchRequest
from app.services.ai.providers import ExplanationProvider
from app.services.dtos import RecommendationCandidate, TrainAnalysis


class AIExplanationService:
    def __init__(self, provider: ExplanationProvider) -> None:
        self._provider = provider

    async def explain_train(
        self,
        query: TrainSearchRequest,
        analysis: TrainAnalysis,
        recommendations: list[RecommendationCandidate],
    ) -> str:
        if not recommendations:
            return self._fallback_no_recommendation(analysis)

        best = recommendations[0]
        direct = analysis.direct_availability
        prompt = self._build_prompt(query, analysis, best)
        provider_text = await self._provider.summarize(prompt)

        if provider_text == prompt:
            return self._template_summary(direct.status, best)
        return provider_text

    def _build_prompt(
        self,
        query: TrainSearchRequest,
        analysis: TrainAnalysis,
        best: RecommendationCandidate,
    ) -> str:
        direct = analysis.direct_availability
        return (
            f"User route: {query.source_station} to {query.destination_station} on "
            f"{query.travel_date} in {query.travel_class.value}. "
            f"Train: {analysis.train.number} {analysis.train.name}. "
            f"Direct status: {direct.status.value}, WL={direct.waitlist_count}, "
            f"RAC={direct.rac_count}, available={direct.available_count}. "
            f"Best segment: {best.segment.source.code} to {best.segment.destination.code}, "
            f"status={best.segment.availability.status.value}, "
            f"score={best.score:.2f}. Explain this as travel intelligence only."
        )

    def _template_summary(
        self,
        direct_status: AvailabilityStatus,
        best: RecommendationCandidate,
    ) -> str:
        segment = best.segment
        if direct_status == AvailabilityStatus.WAITLIST:
            opening = "Direct ticket availability is weak for this train."
        elif direct_status == AvailabilityStatus.RAC:
            opening = "The direct option is RAC, so a stronger segment may be useful."
        else:
            opening = "The direct option is already usable, but this segment is also worth comparing."

        if segment.availability.status == AvailabilityStatus.AVAILABLE:
            segment_text = "confirmed seats are visible"
        elif segment.availability.status == AvailabilityStatus.RAC:
            segment_text = "RAC movement looks better than the direct option"
        else:
            segment_text = "the waitlist is still present but comparatively better"

        return (
            f"{opening} Best intelligence signal: {segment.source.name} "
            f"to {segment.destination.name}, where {segment_text}. "
            "Use this to compare lawful travel options and station practicality before booking manually."
        )

    def _fallback_no_recommendation(self, analysis: TrainAnalysis) -> str:
        direct = analysis.direct_availability
        if direct.status == AvailabilityStatus.AVAILABLE:
            return "Direct availability is already confirmed; no better hidden segment was found."
        return "No high-quality hidden segment was found for this train in the current dataset."

