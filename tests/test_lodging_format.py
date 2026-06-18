import importlib.util
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def _load():
    spec = importlib.util.spec_from_file_location("lodging_ut", ROOT / "agents" / "travel_lodging_agent" / "main.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def test_camping_format_returns_campsite():
    res = _load().run({"destination": "속초", "days": 2, "travel_format": "캠핑/차박"})
    titles = " ".join(i["name"] for i in res["lodging_items"])
    cats = " ".join(i["category"] for i in res["lodging_items"])
    assert "캠핑" in titles or "캠핑" in cats or "차박" in titles

def test_default_format_returns_hotel():
    res = _load().run({"destination": "속초", "days": 2})
    cats = " ".join(i["category"] for i in res["lodging_items"])
    assert "호텔" in cats
