from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from app.schemas.monitor import MonitorCreateRequest
from app.schemas.search import TrainSearchResultResponse


@dataclass
class MonitorRecord:
    request: MonitorCreateRequest
    id: str = field(default_factory=lambda: str(uuid4()))
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_checked_at: datetime | None = None
    last_results: list[TrainSearchResultResponse] = field(default_factory=list)


class MonitorRepository(ABC):
    @abstractmethod
    async def create(self, request: MonitorCreateRequest) -> MonitorRecord:
        raise NotImplementedError

    @abstractmethod
    async def get(self, monitor_id: str) -> MonitorRecord | None:
        raise NotImplementedError

    @abstractmethod
    async def list(self) -> list[MonitorRecord]:
        raise NotImplementedError

    @abstractmethod
    async def update_check_result(
        self,
        monitor_id: str,
        results: list[TrainSearchResultResponse],
    ) -> MonitorRecord | None:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, monitor_id: str) -> bool:
        raise NotImplementedError


class InMemoryMonitorRepository(MonitorRepository):
    def __init__(self) -> None:
        self._records: dict[str, MonitorRecord] = {}

    async def create(self, request: MonitorCreateRequest) -> MonitorRecord:
        record = MonitorRecord(request=request)
        self._records[record.id] = record
        return record

    async def get(self, monitor_id: str) -> MonitorRecord | None:
        return self._records.get(monitor_id)

    async def list(self) -> list[MonitorRecord]:
        return sorted(self._records.values(), key=lambda item: item.created_at, reverse=True)

    async def update_check_result(
        self,
        monitor_id: str,
        results: list[TrainSearchResultResponse],
    ) -> MonitorRecord | None:
        record = self._records.get(monitor_id)
        if record is None:
            return None
        record.last_checked_at = datetime.now(timezone.utc)
        record.last_results = results
        return record

    async def delete(self, monitor_id: str) -> bool:
        return self._records.pop(monitor_id, None) is not None
