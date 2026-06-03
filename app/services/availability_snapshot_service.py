import logging
from dataclasses import dataclass

from app.repositories.availability_snapshot_repository import (
    AvailabilitySnapshotRepository,
    StoredAvailabilitySnapshot,
)
from app.services.dtos import AvailabilitySnapshot

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SnapshotChange:
    previous: StoredAvailabilitySnapshot | None
    current: StoredAvailabilitySnapshot
    meaningful: bool
    reason: str | None = None


class AvailabilitySnapshotService:
    def __init__(self, repository: AvailabilitySnapshotRepository) -> None:
        self._repository = repository

    async def store_snapshot(self, snapshot: AvailabilitySnapshot) -> SnapshotChange:
        previous = await self._repository.latest_for_key(
            snapshot.train_number,
            snapshot.source_station_code,
            snapshot.destination_station_code,
            snapshot.travel_date,
            snapshot.travel_class,
        )
        current = await self._repository.save(snapshot)
        meaningful, reason = self._is_meaningful_change(previous, current)
        logger.info(
            "availability_snapshot_stored",
            extra={
                "train_number": current.train_number,
                "source_station": current.source_station_code,
                "destination_station": current.destination_station_code,
                "status": current.status.value,
                "meaningful_change": meaningful,
                "change_reason": reason,
            },
        )
        return SnapshotChange(previous=previous, current=current, meaningful=meaningful, reason=reason)

    async def store_many(self, snapshots: list[AvailabilitySnapshot]) -> list[SnapshotChange]:
        changes: list[SnapshotChange] = []
        for snapshot in snapshots:
            changes.append(await self.store_snapshot(snapshot))
        return changes

    def _is_meaningful_change(
        self,
        previous: StoredAvailabilitySnapshot | None,
        current: StoredAvailabilitySnapshot,
    ) -> tuple[bool, str | None]:
        if previous is None:
            return True, "first_observation"
        if previous.status != current.status:
            return True, "status_changed"
        if previous.available_count != current.available_count:
            return True, "available_count_changed"
        if previous.rac_count != current.rac_count:
            return True, "rac_count_changed"
        if previous.waitlist_count != current.waitlist_count:
            return True, "waitlist_count_changed"
        return False, None

