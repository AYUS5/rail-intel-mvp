from fastapi import APIRouter, Depends, Response, status

from app.api.deps import get_monitoring_service
from app.schemas.monitor import MonitorCheckResponse, MonitorCreateRequest, MonitorResponse
from app.services.monitoring_service import MonitoringService

router = APIRouter()


@router.post("", response_model=MonitorResponse, status_code=status.HTTP_201_CREATED)
async def create_monitor(
    request: MonitorCreateRequest,
    monitoring_service: MonitoringService = Depends(get_monitoring_service),
) -> MonitorResponse:
    return await monitoring_service.create_monitor(request)


@router.get("", response_model=list[MonitorResponse])
async def list_monitors(
    monitoring_service: MonitoringService = Depends(get_monitoring_service),
) -> list[MonitorResponse]:
    return await monitoring_service.list_monitors()


@router.get("/{monitor_id}", response_model=MonitorResponse)
async def get_monitor(
    monitor_id: str,
    monitoring_service: MonitoringService = Depends(get_monitoring_service),
) -> MonitorResponse:
    return await monitoring_service.get_monitor(monitor_id)


@router.post("/{monitor_id}/check", response_model=MonitorCheckResponse)
async def run_monitor_check(
    monitor_id: str,
    monitoring_service: MonitoringService = Depends(get_monitoring_service),
) -> MonitorCheckResponse:
    return await monitoring_service.run_check(monitor_id)


@router.delete("/{monitor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_monitor(
    monitor_id: str,
    monitoring_service: MonitoringService = Depends(get_monitoring_service),
) -> Response:
    await monitoring_service.delete_monitor(monitor_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

