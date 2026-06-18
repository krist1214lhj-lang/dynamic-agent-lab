import importlib.util
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def _load(agent):
    spec = importlib.util.spec_from_file_location(f"{agent}_ut", ROOT / "agents" / agent / "main.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def test_tour_context_maps_new_themes():
    tour = _load("travel_tour_agent")
    _safe, _loc, _per, _cat, keyword = tour._get_trip_context({"destination": "속초", "themes": ["nature", "wellness"]})
    assert "자연" in keyword or "수목원" in keyword
    assert "온천" in keyword or "스파" in keyword

def test_event_maps_festival_theme():
    ev = _load("travel_event_agent")
    res = ev.run({"destination": "속초", "themes": ["festival"]})
    assert res["event_items"]

def test_food_gourmet_summary():
    food = _load("travel_food_agent")
    res = food.run({"destination": "속초", "themes": ["gourmet"]})
    assert "미슐랭" in res["summary"] or "파인다이닝" in res["summary"] or "베이커리" in res["summary"]
