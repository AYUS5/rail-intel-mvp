from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.availability_snapshot import AvailabilitySnapshotRecord
from app.schemas.common import AvailabilityStatus, TravelClass
from app.services.dtos import AvailabilitySnapshot


@dataclass(frozen=True)
class StoredAvailabilitySnapshot:
    id: int | None
    observed_at: datetime
    train_number: str
    source_station_code: str
    destination_station_code: str
    travel_date: date
    travel_class: TravelClass
    status: AvailabilityStatus
    available_count: int | None
    rac_count: int | None
    waitlist_count: int | None
    provider: str


class AvailabilitySnapshotRepository(ABC):
    @abstractmethod
    async def save(self, snapshot: AvailabilitySnapshot) -> StoredAvailabilitySnapshot:
        raise NotImplementedError

    @abstractmethod
    async def latest_for_key(
        self,
        train_number: str,
        source_station_code: str,
        destination_station_code: str,
        travel_date: date,
        travel_class: TravelClass,
    ) -> StoredAvailabilitySnapshot | None:
        raise NotImplementedError


class SqlAlchemyAvailabilitySnapshotRepository(AvailabilitySnapshotRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, snapshot: AvailabilitySnapshot) -> StoredAvailabilitySnapshot:
        record = AvailabilitySnapshotRecord(
            observed_at=snapshot.checked_at,
            train_number=snapshot.train_number,
            source_station_code=snapshot.source_station_code,
            destination_station_code=snapshot.destination_station_code,
            travel_date=snapshot.travel_date,
            travel_class=snapshot.travel_class.value,
            status=snapshot.status.value,
            available_count=snapshot.available_count,
            rac_count=snapshot.rac_count,
            waitlist_count=snapshot.waitlist_count,
            provider=snapshot.provider,
        )
        self._session.add(record)
        await self._session.flush()
        await self._session.commit()
        return _stored_from_record(record)

    async def latest_for_key(
        self,
        train_number: str,
        source_station_code: str,
        destination_station_code: str,
        travel_date: date,
        travel_class: TravelClass,
    ) -> StoredAvailabilitySnapshot | None:
        statement = (
            select(AvailabilitySnapshotRecord)
            .where(
                AvailabilitySnapshotRecord.train_number == train_number,
                AvailabilitySnapshotRecord.source_station_code == source_station_code,
                AvailabilitySnapshotRecord.destination_station_code == destination_station_code,
                AvailabilitySnapshotRecord.travel_date == travel_date,
                AvailabilitySnapshotRecord.travel_class == travel_class.value,
            )
            .order_by(desc(AvailabilitySnapshotRecord.observed_at))
            .limit(1)
        )
        result = await self._session.execute(statement)
        record = result.scalar_one_or_none()
        return _stored_from_record(record) if record else None


class InMemoryAvailabilitySnapshotRepository(AvailabilitySnapshotRepository):
    def __init__(self) -> None:
        self._records: list[StoredAvailabilitySnapshot] = []
        self._next_id = 1

    async def save(self, snapshot: AvailabilitySnapshot) -> StoredAvailabilitySnapshot:
        record = StoredAvailabilitySnapshot(
            id=self._next_id,
            observed_at=snapshot.checked_at,
            train_number=snapshot.train_number,
            source_station_code=snapshot.source_station_code,
            destination_station_code=snapshot.destination_station_code,
            travel_date=snapshot.travel_date,
            travel_class=snapshot.travel_class,
            status=snapshot.status,
            available_count=snapshot.available_count,
            rac_count=snapshot.rac_count,
            waitlist_count=snapshot.waitlist_count,
            provider=snapshot.provider,
        )
        self._next_id += 1
        self._records.append(record)
        return record

    async def latest_for_key(
        self,
        train_number: str,
        source_station_code: str,
        destination_station_code: str,
        travel_date: date,
        travel_class: TravelClass,
    ) -> StoredAvailabilitySnapshot | None:
        matches = [
            record
            for record in self._records
            if record.train_number == train_number
            and record.source_station_code == source_station_code
            and record.destination_station_code == destination_station_code
            and record.travel_date == travel_date
            and record.travel_class == travel_class
        ]
        return max(matches, key=lambda record: record.observed_at) if matches else None


def _stored_from_record(record: AvailabilitySnapshotRecord) -> StoredAvailabilitySnapshot:
    return StoredAvailabilitySnapshot(
        id=record.id,
        observed_at=record.observed_at,
        train_number=record.train_number,
        source_station_code=record.source_station_code,
        destination_station_code=record.destination_station_code,
        travel_date=record.travel_date,
        travel_class=TravelClass(record.travel_class),
        status=AvailabilityStatus(record.status),
        available_count=record.available_count,
        rac_count=record.rac_count,
        waitlist_count=record.waitlist_count,
        provider=record.provider,
    )

