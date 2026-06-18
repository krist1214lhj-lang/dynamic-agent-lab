"""추천의 인원수(people)가 워크플로우→예산 에이전트까지 전달되어야 한다.

전달이 안 되면 상세 예산이 항상 1인 기준이라 추천 카드(N인 총액)와 불일치한다.
"""

import re
from fastapi.testclient import TestClient

import main

client = TestClient(main.app)

BASE = {
    "user_request": "",
    "destination": "속초",
    "origin": "서울",
    "days": 5,
    "budget_level": "medium",
    "requested_features": ["budget"],
    "additional_conditions": {"themes": []},
}


def _budget_total(payload):
    resp = client.post("/run-workflow", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    budget = next(r for r in data["agent_results"] if "budget" in r.get("agent", ""))
    total = int(re.sub(r"[^0-9]", "", budget["total"]))
    return total, data


def test_people_propagates_to_budget():
    one, _ = _budget_total({**BASE, "people": 1})
    two, data = _budget_total({**BASE, "people": 2})
    assert two > one, f"people=2 예산({two})이 people=1({one})보다 커야 함"
    assert data["input_data"].get("people") == 2


def test_people_defaults_to_one():
    base_total, _ = _budget_total(BASE)  # people 미지정
    one, _ = _budget_total({**BASE, "people": 1})
    assert base_total == one
