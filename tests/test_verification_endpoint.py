from fastapi.testclient import TestClient
import main

client = TestClient(main.app)

BASE = {"user_request": "", "destination": "속초", "origin": "서울", "days": 3,
        "budget_level": "medium", "requested_features": ["budget", "schedule", "lodging"],
        "additional_conditions": {"themes": []}}


def _run(**over):
    r = client.post("/run-workflow", json={**BASE, **over})
    assert r.status_code == 200, r.text
    return r.json()


def test_response_has_verification_report():
    d = _run()
    assert "verification_report" in d
    assert d["verification_report"]["engine"] in ("rule_only", "rule+llm")


def test_day_trip_excludes_lodging_card():
    d = _run(travel_format="당일치기", days=3)
    assert all("lodging" not in r["agent"] for r in d["agent_results"])
    assert any(e["reason"] == "day_trip_no_lodging" for e in d["verification_report"]["excluded"])
