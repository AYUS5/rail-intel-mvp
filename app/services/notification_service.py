import logging

from app.repositories.monitor_repository import MonitorRecord
from app.schemas.search import TrainSearchResultResponse

logger = logging.getLogger(__name__)


class NotificationService:
    async def send_availability_alert(
        self,
        monitor: MonitorRecord,
        matched_results: list[TrainSearchResultResponse],
    ) -> None:
        if not monitor.request.notification_target:
            logger.info("Monitor %s matched but has no notification target", monitor.id)
            return
        logger.info(
            "Would send availability alert for monitor %s to %s with %d results",
            monitor.id,
            monitor.request.notification_target,
            len(matched_results),
        )

