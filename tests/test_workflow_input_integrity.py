"""F-5: 사용자 제공 additional_conditions가 확정 입력(destination/days/people/budget_level)을
덮어쓰지 못해야 한다. 정상적인 추가 조건(themes/companions/priority)은 그대로 흘러야 한다.
"""

from fastapi.testclient import TestClient

import main

client = TestClient(main.app)

BASE = {
    "user_request": "",
    "destination": "속초",
    "origin": "서울",
    "days": 3,
    "people": 2,
    "budget_level": "medium",
    "requested_features": ["budget"],
}


def test_additional_conditions_cannot_override_confirmed_fields():
    payload = {
        **BASE,
        "additional_conditions": {
            "destination": "HACKED",
            "days": 99999,
            "people": 100000,
            "budget_level": "luxury",
            "themes": ["nature"],
            "companions": ["solo"],
            "priority": "cost",
        },
    }
    r = client.post("/run-workflow", json=payload)
    assert r.status_code == 200, r.text
    idata = r.json()["input_data"]
    # 확정 입력은 검증된 값을 유지한다.
    assert idata["destination"] == "속초"
    assert idata["days"] == 3
    assert idata["people"] == 2
    assert idata["budget_level"] == "medium"
    # 정상 추가 조건은 그대로 전달된다.
    assert idata.get("themes") == ["nature"]
    assert idata.get("companions") == ["solo"]
    assert idata.get("priority") == "cost"
