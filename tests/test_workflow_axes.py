from fastapi.testclient import TestClient
import main

client = TestClient(main.app)

BASE = {
    "user_request": "", "destination": "속초", "origin": "서울",
    "days": 3, "budget_level": "medium", "requested_features": ["budget", "schedule", "lodging"],
    "additional_conditions": {"themes": []},
}

def _run(**over):
    payload = {**BASE, **over}
    r = client.post("/run-workflow", json=payload)
    assert r.status_code == 200, r.text
    return r.json()

def test_new_axes_injected_into_input_data():
    d = _run(travel_format="기차여행", transport_mode="기차/KTX", pace="여유")
    assert d["input_data"]["travel_format"] == "기차여행"
    assert d["input_data"]["transport_mode"] == "기차/KTX"
    assert d["input_data"]["pace"] == "여유"

def test_day_trip_forces_one_day():
    d = _run(travel_format="당일치기", days=5)
    assert d["input_data"]["days"] == 1

def test_family_kids_theme_adds_family_companion():
    d = _run(additional_conditions={"themes": ["family_kids"], "companions": []})
    assert "family" in d["input_data"]["companions"]
