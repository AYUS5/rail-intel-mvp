import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone

from app.schemas.common import AvailabilityStatus, TravelClass
from app.services.dtos import (
    AvailabilitySnapshot,
    SegmentOpportunity,
    StationStop,
    TrainAnalysis,
    TrainRoute,
)
from app.services.railway_service import RailwayService
from app.utils.request_context import get_request_id
from app.utils.scoring import classify_coverage, score_candidate

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RouteAnalysisConfig:
    max_station_extension: int = 2
    min_overlap_ratio: float = 0.35
    max_candidates_per_train: int = 12
    availability_timeout_seconds: float = 8.0
    availability_concurrency: int = 12


@dataclass(frozen=True)
class CandidatePair:
    source_index: int
    destination_index: int
    source: StationStop
    destination: StationStop
    overlap_ratio: float


class RouteAnalysisService:
    def __init__(
        self,
        railway_service: RailwayService,
        config: RouteAnalysisConfig | None = None,
    ) -> None:
        self._railway_service = railway_service
        self._config = config or RouteAnalysisConfig()

    async def analyze_search(
        self,
        source_station: str,
        destination_station: str,
        travel_date: date,
        travel_class: TravelClass,
        max_results: int,
    ) -> list[TrainAnalysis]:
        trains = await self._railway_service.search_trains(
            source_station,
            destination_station,
            travel_date,
            travel_class,
        )
        start = time.perf_counter()
        tasks = [
            self.analyze_train(
                train,
                source_station,
                destination_station,
                travel_date,
                travel_class,
            )
            for train in trains[:max_results]
        ]
        gathered = await asyncio.gather(*tasks, return_exceptions=True)
        analyses: list[TrainAnalysis] = []
        for train, result in zip(trains[:max_results], gathered, strict=False):
            if isinstance(result, Exception):
                logger.exception(
                    "route_analysis_train_failed",
                    extra={
                        "train_number": train.number,
                        "error": str(result),
                        "request_id": get_request_id(),
                    },
                )
                continue
            if result is not None:
                analyses.append(result)
        logger.info(
            "route_analysis_search_complete",
            extra={
                "source_station": source_station,
                "destination_station": destination_station,
                "travel_class": travel_class.value,
                "train_count": len(trains[:max_results]),
                "analysis_count": len(analyses),
                "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                "request_id": get_request_id(),
            },
        )
        return analyses

    async def analyze_train(
        self,
        train: TrainRoute,
        source_station: str,
        destination_station: str,
        travel_date: date,
        travel_class: TravelClass,
    ) -> TrainAnalysis | None:
        source_code = self._railway_service.normalize_station_code(source_station)
        destination_code = self._railway_service.normalize_station_code(destination_station)
        index = train.index_by_station_code()
        if source_code not in index or destination_code not in index:
            logger.info(
                "route_analysis_station_pair_missing",
                extra={"train_number": train.number, "request_id": get_request_id()},
            )
            return None
        requested_source_index = index[source_code]
        requested_destination_index = index[destination_code]
        if requested_source_index >= requested_destination_index:
            logger.info(
                "route_analysis_invalid_station_order",
                extra={"train_number": train.number, "request_id": get_request_id()},
            )
            return None

        start = time.perf_counter()
        direct_availability = await self._safe_get_availability(
            train.number,
            source_code,
            destination_code,
            travel_date,
            travel_class,
        )

        candidate_pairs: list[CandidatePair] = []
        route_last_index = len(train.stops) - 1
        lower_bound = max(0, requested_source_index - self._config.max_station_extension)
        upper_bound = min(
            route_last_index,
            requested_destination_index + self._config.max_station_extension,
        )
        requested_span = requested_destination_index - requested_source_index

        for candidate_source_index in range(lower_bound, requested_destination_index + 1):
            min_destination = max(candidate_source_index + 1, requested_source_index + 1)
            for candidate_destination_index in range(min_destination, upper_bound + 1):
                if (
                    candidate_source_index == requested_source_index
                    and candidate_destination_index == requested_destination_index
                ):
                    continue

                overlap_intervals = max(
                    0,
                    min(candidate_destination_index, requested_destination_index)
                    - max(candidate_source_index, requested_source_index),
                )
                if overlap_intervals <= 0:
                    continue

                overlap_ratio = overlap_intervals / requested_span
                keeps_boundary = (
                    candidate_source_index == requested_source_index
                    or candidate_destination_index == requested_destination_index
                )
                if overlap_ratio < self._config.min_overlap_ratio and not keeps_boundary:
                    continue

                source_stop = train.stops[candidate_source_index]
                destination_stop = train.stops[candidate_destination_index]
                candidate_pairs.append(
                    CandidatePair(
                        source_index=candidate_source_index,
                        destination_index=candidate_destination_index,
                        source=source_stop,
                        destination=destination_stop,
                        overlap_ratio=round(overlap_ratio, 4),
                    )
                )

        availabilities = await self._fetch_candidate_availability(
            train.number,
            candidate_pairs,
            travel_date,
            travel_class,
        )

        candidates: list[SegmentOpportunity] = []
        for pair, availability in zip(candidate_pairs, availabilities, strict=False):
            if availability is None:
                continue

            score = score_candidate(
                availability,
                direct_availability,
                pair.overlap_ratio,
                pair.source_index,
                pair.destination_index,
                requested_source_index,
                requested_destination_index,
            )

            if score.usefulness_score <= 0.2:
                continue

            coverage_type = classify_coverage(
                pair.source_index,
                pair.destination_index,
                requested_source_index,
                requested_destination_index,
            )
            candidates.append(
                SegmentOpportunity(
                    train_number=train.number,
                    source=pair.source,
                    destination=pair.destination,
                    availability=availability,
                    coverage_type=coverage_type,
                    overlap_ratio=pair.overlap_ratio,
                    route_mismatch_score=score.route_mismatch_score,
                    confirmation_probability=score.confirmation_probability,
                    usefulness_score=score.usefulness_score,
                    distance_km=pair.destination.distance_km - pair.source.distance_km,
                    reason_codes=score.reason_codes,
                )
            )

        candidates.sort(
            key=lambda item: (
                item.usefulness_score,
                item.confirmation_probability,
                item.overlap_ratio,
                -item.route_mismatch_score,
            ),
            reverse=True,
        )

        analysis = TrainAnalysis(
            train=train,
            direct_availability=direct_availability,
            hidden_segments=tuple(candidates[: self._config.max_candidates_per_train]),
            pairs_considered=len(candidate_pairs),
        )
        logger.info(
            "route_analysis_train_complete",
            extra={
                "train_number": train.number,
                "pairs_considered": len(candidate_pairs),
                "hidden_segments": len(analysis.hidden_segments),
                "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                "request_id": get_request_id(),
            },
        )
        return analysis

    async def _fetch_candidate_availability(
        self,
        train_number: str,
        candidate_pairs: list[CandidatePair],
        travel_date: date,
        travel_class: TravelClass,
    ) -> list[AvailabilitySnapshot | None]:
        start = time.perf_counter()
        semaphore = asyncio.Semaphore(max(1, self._config.availability_concurrency))

        async def fetch(pair: CandidatePair) -> AvailabilitySnapshot | None:
            async with semaphore:
                return await self._safe_get_availability(
                    train_number,
                    pair.source.code,
                    pair.destination.code,
                    travel_date,
                    travel_class,
                )

        results = await asyncio.gather(
            *(fetch(pair) for pair in candidate_pairs),
            return_exceptions=True,
        )

        availabilities: list[AvailabilitySnapshot | None] = []
        for pair, result in zip(candidate_pairs, results, strict=False):
            if isinstance(result, Exception):
                logger.warning(
                    "candidate_availability_failed",
                    extra={
                        "train_number": train_number,
                        "source_station": pair.source.code,
                        "destination_station": pair.destination.code,
                        "error": str(result),
                        "request_id": get_request_id(),
                    },
                )
                availabilities.append(None)
            else:
                availabilities.append(result)
        logger.info(
            "candidate_availability_batch_complete",
            extra={
                "train_number": train_number,
                "candidate_count": len(candidate_pairs),
                "successful_count": sum(item is not None for item in availabilities),
                "concurrency_limit": self._config.availability_concurrency,
                "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                "request_id": get_request_id(),
            },
        )
        return availabilities

    async def _safe_get_availability(
        self,
        train_number: str,
        source_station: str,
        destination_station: str,
        travel_date: date,
        travel_class: TravelClass,
    ) -> AvailabilitySnapshot:
        start = time.perf_counter()
        try:
            snapshot = await asyncio.wait_for(
                self._railway_service.get_availability(
                    train_number,
                    source_station,
                    destination_station,
                    travel_date,
                    travel_class,
                ),
                timeout=self._config.availability_timeout_seconds,
            )
            logger.info(
                "availability_fetch_complete",
                extra={
                    "train_number": train_number,
                    "source_station": source_station,
                    "destination_station": destination_station,
                    "status": snapshot.status.value,
                    "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                    "request_id": get_request_id(),
                },
            )
            return snapshot
        except Exception as exc:
            logger.warning(
                "availability_fetch_failed",
                extra={
                    "train_number": train_number,
                    "source_station": source_station,
                    "destination_station": destination_station,
                    "error": str(exc),
                    "request_id": get_request_id(),
                },
            )
            return AvailabilitySnapshot(
                train_number=train_number,
                source_station_code=source_station,
                destination_station_code=destination_station,
                travel_date=travel_date,
                travel_class=travel_class,
                status=AvailabilityStatus.UNKNOWN,
                checked_at=datetime.now(timezone.utc),
                provider="fallback",
            )
