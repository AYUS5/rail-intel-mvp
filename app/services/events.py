import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.utils.request_context import get_request_id

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DomainEvent:
    event_type: str
    payload: dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class EventPublisher(ABC):
    @abstractmethod
    async def publish(self, event: DomainEvent) -> None:
        raise NotImplementedError


class LoggingEventPublisher(EventPublisher):
    async def publish(self, event: DomainEvent) -> None:
        logger.info(
            "domain_event_published",
            extra={
                "event_id": event.event_id,
                "event_type": event.event_type,
                "occurred_at": event.occurred_at.isoformat(),
                "payload": event.payload,
                "request_id": get_request_id(),
            },
        )

