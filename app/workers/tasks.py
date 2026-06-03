import asyncio
from datetime import datetime, timezone

from app.api.deps import get_route_analysis_service
from app.db.session import AsyncSessionLocal
from app.repositories.availability_snapshot_repository import (
    SqlAlchemyAvailabilitySnapshotRepository,
)
from app.schemas.monitor import MonitorCreateRequest
from app.services.availability_snapshot_service import AvailabilitySnapshotService
from app.services.dtos import AvailabilitySnapshot
from app.services.dtos import TrainAnalysis
from app.services.events import DomainEvent, LoggingEventPublisher
from app.workers.celery_app import celery_app


@celery_app.task(
    bind=True,
    name="monitor_availability",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def monitor_availability(self, payload: dict) -> dict:
    """Run a monitor check from a serialized payload.

    Production deployments should load monitor definitions from PostgreSQL and dispatch
    notifications through a durable provider.
    """

    request = MonitorCreateRequest.model_validate(payload)
    return asyncio.run(_run_monitor_payload(request))


@celery_app.task(
    bind=True,
    name="capture_monitor_snapshots",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def capture_monitor_snapshots(self, payload: dict) -> dict:
    request = MonitorCreateRequest.model_validate(payload)
    return asyncio.run(_capture_monitor_snapshots(request))


async def _run_monitor_payload(request: MonitorCreateRequest) -> dict:
    capture_result = await _capture_monitor_snapshots(request)
    return {
        "checked_at": capture_result["checked_at"],
        "matches": capture_result["matches"],
        "top_trains": capture_result["top_trains"],
        "snapshots_stored": capture_result["snapshots_stored"],
        "meaningful_changes": capture_result["meaningful_changes"],
    }


async def _capture_monitor_snapshots(request: MonitorCreateRequest) -> dict:
    service = get_route_analysis_service()
    analyses = await service.analyze_search(
        request.source_station,
        request.destination_station,
        request.travel_date,
        request.travel_class,
        max_results=25,
    )
    if request.train_number:
        analyses = [analysis for analysis in analyses if analysis.train.number == request.train_number]

    snapshots = _snapshots_from_analyses(analyses)
    async with AsyncSessionLocal() as session:
        repository = SqlAlchemyAvailabilitySnapshotRepository(session)
        snapshot_service = AvailabilitySnapshotService(repository)
        changes = await snapshot_service.store_many(snapshots)
    event_publisher = LoggingEventPublisher()
    for change in changes:
        if change.meaningful:
            await event_publisher.publish(
                DomainEvent(
                    event_type="availability.meaningful_change",
                    payload={
                        "train_number": change.current.train_number,
                        "source_station_code": change.current.source_station_code,
                        "destination_station_code": change.current.destination_station_code,
                        "travel_date": change.current.travel_date.isoformat(),
                        "travel_class": change.current.travel_class.value,
                        "status": change.current.status.value,
                        "reason": change.reason,
                    },
                )
            )

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "matches": len(analyses),
        "top_trains": [analysis.train.number for analysis in analyses[:5]],
        "snapshots_stored": len(changes),
        "meaningful_changes": sum(1 for change in changes if change.meaningful),
    }


def _snapshots_from_analyses(analyses: list[TrainAnalysis]) -> list[AvailabilitySnapshot]:
    snapshots: list[AvailabilitySnapshot] = []
    for analysis in analyses:
        snapshots.append(analysis.direct_availability)
        snapshots.extend(segment.availability for segment in analysis.hidden_segments)
    return snapshots
