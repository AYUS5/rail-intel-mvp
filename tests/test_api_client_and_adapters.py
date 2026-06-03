from datetime import date

import httpx
import pytest

from app.adapters.railway_response_adapter import RailwayResponseAdapter
from app.api_client.http import AsyncHttpClient, AsyncHttpClientConfig, RetryPolicy
from app.repositories.railway_provider import RailwayProviderUnavailableError
from app.schemas.common import AvailabilityStatus, TravelClass


@pytest.mark.asyncio
async def test_async_http_client_retries_retryable_status() -> None:
    attempts = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        assert request.headers["x-request-id"]
        if attempts == 1:
            return httpx.Response(503, json={"error": "temporary"})
        return httpx.Response(200, json={"ok": True})

    client = AsyncHttpClient(
        AsyncHttpClientConfig(
            base_url="https://rail.example.test",
            retry_policy=RetryPolicy(max_attempts=2, base_backoff_seconds=0),
        ),
        transport=httpx.MockTransport(handler),
    )

    try:
        payload = await client.get_json("/availability", params={"train_number": "12952"})
    finally:
        await client.aclose()

    assert payload == {"ok": True}
    assert attempts == 2


def test_railway_response_adapter_normalizes_external_payloads() -> None:
    adapter = RailwayResponseAdapter()

    route = adapter.parse_train_route(
        {
            "train_number": "12952",
            "train_name": "Mumbai Rajdhani Express",
            "stations": [
                {"station_code": "ndls", "station_name": "New Delhi", "distance": "0"},
                {"station_code": "mmct", "station_name": "Mumbai Central", "distance": "1384"},
            ],
        }
    )
    availability = adapter.parse_availability(
        {
            "data": {
                "status": "WL",
                "wl": "120",
                "source": "ndls",
                "destination": "mmct",
            }
        },
        "12952",
        "NDLS",
        "MMCT",
        date(2026, 6, 15),
        TravelClass.THIRD_AC,
    )

    assert route.number == "12952"
    assert route.stops[0].code == "NDLS"
    assert availability.status == AvailabilityStatus.WAITLIST
    assert availability.waitlist_count == 120


def test_railway_response_adapter_rejects_malformed_route() -> None:
    adapter = RailwayResponseAdapter()

    with pytest.raises(RailwayProviderUnavailableError):
        adapter.parse_train_route({"number": "12952", "stops": []})

