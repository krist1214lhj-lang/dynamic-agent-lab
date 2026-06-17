from fastapi.testclient import TestClient
import main

client = TestClient(main.app)


def test_recommend_returns_candidates():
    resp = client.post("/recommend", json={"budget_total": 1500000, "people": 2, "days": 3, "themes": ["healing"]})
    assert resp.status_code == 200
    data = resp.json()
    assert "recommendations" in data
    assert len(data["recommendations"]) <= 5
    if data["recommendations"]:
        r = data["recommendations"][0]
        assert "destination" in r and "est_total" in r and "within_budget" in r
