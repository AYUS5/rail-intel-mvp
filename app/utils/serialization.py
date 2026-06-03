from datetime import date, datetime
from typing import Any

from app.schemas.common import AvailabilityStatus, TravelClass
from app.services.dtos import AvailabilitySnapshot, StationStop, TrainRoute


def station_stop_to_dict(stop: StationStop) -> dict[str, Any]:
    return {
        "code": stop.code,
        "name": stop.name,
        "sequence": stop.sequence,
        "distance_km": stop.distance_km,
        "arrival": stop.arrival,
        "departure": stop.departure,
    }


def station_stop_from_dict(payload: dict[str, Any]) -> StationStop:
    return StationStop(
        code=str(payload["code"]),
        name=str(payload["name"]),
        sequence=int(payload["sequence"]),
        distance_km=int(payload["distance_km"]),
        arrival=payload.get("arrival"),
        departure=payload.get("departure"),
    )


def train_route_to_dict(route: TrainRoute) -> dict[str, Any]:
    return {
        "number": route.number,
        "name": route.name,
        "origin_station_code": route.origin_station_code,
        "destination_station_code": route.destination_station_code,
        "stops": [station_stop_to_dict(stop) for stop in route.stops],
    }


def train_route_from_dict(payload: dict[str, Any]) -> TrainRoute:
    return TrainRoute(
        number=str(payload["number"]),
        name=str(payload["name"]),
        origin_station_code=str(payload["origin_station_code"]),
        destination_station_code=str(payload["destination_station_code"]),
        stops=tuple(station_stop_from_dict(stop) for stop in payload["stops"]),
    )


def availability_to_dict(snapshot: AvailabilitySnapshot) -> dict[str, Any]:
    return {
        "train_number": snapshot.train_number,
        "source_station_code": snapshot.source_station_code,
        "destination_station_code": snapshot.destination_station_code,
        "travel_date": snapshot.travel_date.isoformat(),
        "travel_class": snapshot.travel_class.value,
        "status": snapshot.status.value,
        "available_count": snapshot.available_count,
        "rac_count": snapshot.rac_count,
        "waitlist_count": snapshot.waitlist_count,
        "checked_at": snapshot.checked_at.isoformat(),
        "provider": snapshot.provider,
    }


def availability_from_dict(payload: dict[str, Any]) -> AvailabilitySnapshot:
    return AvailabilitySnapshot(
        train_number=str(payload["train_number"]),
        source_station_code=str(payload["source_station_code"]),
        destination_station_code=str(payload["destination_station_code"]),
        travel_date=date.fromisoformat(str(payload["travel_date"])),
        travel_class=TravelClass(str(payload["travel_class"])),
        status=AvailabilityStatus(str(payload["status"])),
        available_count=payload.get("available_count"),
        rac_count=payload.get("rac_count"),
        waitlist_count=payload.get("waitlist_count"),
        checked_at=datetime.fromisoformat(str(payload["checked_at"])),
        provider=str(payload.get("provider", "unknown")),
    )

