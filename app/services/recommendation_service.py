from app.schemas.common import AvailabilityStatus, CoverageType
from app.services.dtos import RecommendationCandidate, SegmentOpportunity, TrainAnalysis


class RecommendationService:
    def rank_train_recommendations(
        self,
        analysis: TrainAnalysis,
        limit: int = 3,
    ) -> list[RecommendationCandidate]:
        ranked_segments = sorted(
            analysis.hidden_segments,
            key=lambda item: (
                item.usefulness_score,
                item.confirmation_probability,
                item.overlap_ratio,
            ),
            reverse=True,
        )
        recommendations: list[RecommendationCandidate] = []
        for rank, segment in enumerate(ranked_segments[:limit], start=1):
            recommendations.append(
                RecommendationCandidate(
                    rank=rank,
                    train_number=analysis.train.number,
                    title=self._title_for_segment(segment),
                    score=segment.usefulness_score,
                    confidence=self._confidence_for_segment(segment),
                    segment=segment,
                    explanation=self._explain_segment(analysis, segment),
                )
            )
        return recommendations

    def _title_for_segment(self, segment: SegmentOpportunity) -> str:
        if segment.coverage_type == CoverageType.LATER_BOARDING_TO_DESTINATION:
            return f"Board from {segment.source.name} for the same destination"
        if segment.coverage_type == CoverageType.SAME_BOARDING_PARTIAL:
            return f"Confirmed/RAC partial ride up to {segment.destination.name}"
        if segment.coverage_type == CoverageType.EXTENDED_COVERAGE:
            return "Check nearby station quota with full route coverage"
        return f"Useful segment from {segment.source.name} to {segment.destination.name}"

    def _confidence_for_segment(self, segment: SegmentOpportunity) -> float:
        if segment.availability.status == AvailabilityStatus.AVAILABLE:
            return min(0.98, segment.confirmation_probability)
        if segment.availability.status == AvailabilityStatus.RAC:
            return min(0.78, segment.confirmation_probability)
        return min(0.55, segment.confirmation_probability)

    def _explain_segment(self, analysis: TrainAnalysis, segment: SegmentOpportunity) -> str:
        direct = analysis.direct_availability
        if segment.availability.status == AvailabilityStatus.AVAILABLE:
            availability_text = "confirmed seats are available"
        elif segment.availability.status == AvailabilityStatus.RAC:
            availability_text = f"RAC {segment.availability.rac_count or ''}".strip()
        else:
            availability_text = f"waitlist {segment.availability.waitlist_count or ''}".strip()

        direct_text = direct.status.value
        if direct.waitlist_count is not None:
            direct_text = f"WL {direct.waitlist_count}"
        elif direct.rac_count is not None:
            direct_text = f"RAC {direct.rac_count}"

        return (
            f"Direct availability is {direct_text}. "
            f"The segment {segment.source.code} to {segment.destination.code} has "
            f"{availability_text}, covers {segment.overlap_ratio:.0%} of the requested route, "
            "and has a better practical score than the direct option."
        )

    def rank_across_trains(
        self,
        analyses: list[TrainAnalysis],
        limit: int = 5,
    ) -> list[RecommendationCandidate]:
        combined: list[RecommendationCandidate] = []
        for analysis in analyses:
            combined.extend(self.rank_train_recommendations(analysis, limit=limit))
        combined.sort(key=lambda item: (item.score, item.confidence), reverse=True)
        return [
            RecommendationCandidate(
                rank=index,
                train_number=item.train_number,
                title=item.title,
                score=item.score,
                confidence=item.confidence,
                segment=item.segment,
                explanation=item.explanation,
            )
            for index, item in enumerate(combined[:limit], start=1)
        ]

