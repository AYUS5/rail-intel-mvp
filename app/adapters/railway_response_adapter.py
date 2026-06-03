from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from app.repositories.railway_provider import RailwayProviderUnavailableError
from app.schemas.common import AvailabilityStatus, TravelClass
from app.services.dtos import AvailabilitySnapshot, StationStop, TrainRoute


class RailwayResponseAdapter:
    def normalize_station_code(self, station: str) -> str:
        return " ".join(station.upper().split())

    def parse_train_search(self, payload: dict[str, Any]) -> list[TrainRoute]:
        trains_payload = payload.get("trains")
        if trains_payload is None:
            trains_payload = payload.get("data", {}).get("trains") if isinstance(payload.get("data"), dict) else None
        if trains_payload is None:
            return []
        if not isinstance(trains_payload, list):
            raise RailwayProviderUnavailableError("Provider train search payload is malformed")
        return [self.parse_train_route(item) for item in trains_payload if isinstance(item, dict)]

    def parse_train_route_response(self, payload: dict[str, Any]) -> TrainRoute | None:
        route_payload = payload.get("train") or payload.get("route") or payload.get("data") or payload
        if not route_payload:
            return None
        if not isinstance(route_payload, dict):
            raise RailwayProviderUnavailableError("Provider route payload is malformed")
        return self.parse_train_route(route_payload)

    def parse_train_route(self, payload: dict[str, Any]) -> TrainRoute:
        train_number = payload.get("number") or payload.get("train_number")
        if not train_number:
            raise RailwayProviderUnavailableError("Provider route payload missing train number")

        stops_payload = payload.get("stops") or payload.get("route") or payload.get("stations")
        if not isinstance(stops_payload, list) or not stops_payload:
            raise RailwayProviderUnavailableError("Provider route payload has no stops")

        stops = tuple(self._parse_stop(stop, index) for index, stop in enumerate(stops_payload))
        return TrainRoute(
            number=str(train_number),
            name=str(payload.get("name") or payload.get("train_name") or train_number),
            origin_station_code=self.normalize_station_code(
                str(payload.get("origin_station_code") or stops[0].code)
            ),
            destination_station_code=self.normalize_station_code(
                str(payload.get("destination_station_code") or stops[-1].code)
            ),
            stops=stops,
        )

    def parse_availability(
        self,
        payload: dict[str, Any],
        train_number: str,
        source_station: str,
        destination_station: str,
        travel_date: date,
        travel_class: TravelClass,
    ) -> AvailabilitySnapshot:
        data = payload.get("availability") or payload.get("data") or payload
        if not isinstance(data, dict):
            raise RailwayProviderUnavailableError("Provider availability payload is malformed")

        return AvailabilitySnapshot(
            train_number=str(data.get("train_number") or train_number),
            source_station_code=self.normalize_station_code(
                str(data.get("source_station_code") or data.get("source") or source_station)
            ),
            destination_station_code=self.normalize_station_code(
                str(data.get("destination_station_code") or data.get("destination") or destination_station)
            ),
            travel_date=travel_date,
            travel_class=travel_class,
            status=self._parse_status(data.get("status")),
            available_count=self._optional_int(data.get("available_count") or data.get("available")),
            rac_count=self._optional_int(data.get("rac_count") or data.get("rac")),
            waitlist_count=self._optional_int(data.get("waitlist_count") or data.get("wl")),
            checked_at=self._parse_checked_at(data.get("checked_at") or data.get("timestamp")),
            provider=str(data.get("provider", "real")),
        )

    def _parse_stop(self, payload: Any, index: int) -> StationStop:
        if not isinstance(payload, dict):
            raise RailwayProviderUnavailableError("Provider stop payload is malformed")
        code = payload.get("code") or payload.get("station_code")
        if not code:
            raise RailwayProviderUnavailableError("Provider stop payload missing station code")
        return StationStop(
            code=self.normalize_station_code(str(code)),
            name=str(payload.get("name") or payload.get("station_name") or code),
            sequence=int(payload.get("sequence", index)),
            distance_km=int(payload.get("distance_km") or payload.get("distance") or 0),
            arrival=payload.get("arrival") or payload.get("arrival_time"),
            departure=payload.get("departure") or payload.get("departure_time"),
        )

    def _parse_status(self, value: Any) -> AvailabilityStatus:
        if value is None:
            return AvailabilityStatus.UNKNOWN
        normalized = str(value).upper().replace(" ", "_")
        aliases = {
            "AVL": AvailabilityStatus.AVAILABLE,
            "AVAILABLE": AvailabilityStatus.AVAILABLE,
            "CONFIRMED": AvailabilityStatus.AVAILABLE,
            "RAC": AvailabilityStatus.RAC,
            "WL": AvailabilityStatus.WAITLIST,
            "WAITLIST": AvailabilityStatus.WAITLIST,
            "WAIT_LIST": AvailabilityStatus.WAITLIST,
            "NOT_AVAILABLE": AvailabilityStatus.NOT_AVAILABLE,
            "REGRET": AvailabilityStatus.NOT_AVAILABLE,
        }
        return aliases.get(normalized, AvailabilityStatus.UNKNOWN)

    def _parse_checked_at(self, value: Any) -> datetime:
        if not value:
            return datetime.now(timezone.utc)
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return datetime.now(timezone.utc)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

    def _optional_int(self, value: Any) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

