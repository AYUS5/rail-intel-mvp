from fastapi.testclient import TestClient

from app.main import app


def test_search_endpoint_returns_hidden_segments() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/search/trains",
        json={
            "source_station": "Delhi",
            "destination_station": "Mumbai",
            "travel_date": "2026-06-15",
            "travel_class": "3AC",
            "max_results": 5,
            "include_explanations": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["safety_notice"].startswith("This platform analyzes availability")
    assert body["results"]
    assert body["results"][0]["direct_availability"]["status"] == "WAITLIST"
    hidden_pairs = {
        (segment["source"]["code"], segment["destination"]["code"])
        for segment in body["results"][0]["hidden_segments"]
    }
    assert ("MTJ", "MMCT") in hidden_pairs


def test_monitor_create_and_check() -> None:
    client = TestClient(app)

    create_response = client.post(
        "/api/v1/monitors",
        json={
            "source_station": "Delhi",
            "destination_station": "Mumbai",
            "travel_date": "2026-06-15",
            "travel_class": "3AC",
            "train_number": "12952",
            "threshold_status": "RAC",
            "notification_target": "ops@example.com",
        },
    )

    assert create_response.status_code == 201
    monitor_id = create_response.json()["id"]
    check_response = client.post(f"/api/v1/monitors/{monitor_id}/check")
    assert check_response.status_code == 200
    assert check_response.json()["alert_triggered"] is True

