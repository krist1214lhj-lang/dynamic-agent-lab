"""mock_fallback 시 tour/food 에이전트가 목적지를 무시하고 서울로 하드코딩하던 버그 회귀 방지.

서비스 키가 없으면 tour/food는 mock을 반환하는데, 등록 안 된 목적지(속초 등)는
서울 명소/맛집을 보여줬다(추천지 불일치). 미등록 목적지는 목적지 기반 일반 항목을
반환해야 하고, 등록된 부산/서울은 기존 데이터를 유지해야 한다.
"""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(agent_dir):
    spec = importlib.util.spec_from_file_location(
        f"{agent_dir}_under_test",
        ROOT / "agents" / agent_dir / "main.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SEOUL_TOUR = ["경복궁", "남산서울타워", "북촌한옥마을"]
SEOUL_FOOD = ["삼청동", "성수동", "명동"]


# --- tour ---
def test_tour_mock_unknown_destination_is_destination_aware():
    tour = _load("travel_tour_agent")
    res = tour.build_mock_tour_result({"destination": "속초", "location": "속초", "days": 5})
    titles = " ".join(i["title"] for i in res["tour_items"])
    for seoul in SEOUL_TOUR:
        assert seoul not in titles, f"속초 mock에 서울 명소 {seoul} 포함됨"
    assert "속초" in titles


def test_tour_mock_busan_preserved():
    tour = _load("travel_tour_agent")
    res = tour.build_mock_tour_result({"destination": "부산", "location": "부산"})
    assert any("해운대" in i["title"] for i in res["tour_items"])


def test_tour_mock_seoul_preserved():
    tour = _load("travel_tour_agent")
    res = tour.build_mock_tour_result({"destination": "서울", "location": "서울"})
    assert any("경복궁" in i["title"] for i in res["tour_items"])


# --- food ---
def test_food_mock_unknown_destination_is_destination_aware():
    food = _load("travel_food_agent")
    res = food.run({"destination": "속초"})
    names = " ".join(i["name"] for i in res["food_items"])
    for seoul in SEOUL_FOOD:
        assert seoul not in names, f"속초 food mock에 서울 지명 {seoul} 포함됨"
    assert "속초" in names


def test_food_known_destinations_preserved():
    food = _load("travel_food_agent")
    busan = food.run({"destination": "부산"})["food_items"]
    seoul = food.run({"destination": "서울"})["food_items"]
    assert any("해운대" in i["name"] for i in busan)
    assert any("삼청동" in i["name"] for i in seoul)
