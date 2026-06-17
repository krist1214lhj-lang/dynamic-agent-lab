import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    p = ROOT / "agents" / "travel_recommender_agent" / "main.py"
    spec = importlib.util.spec_from_file_location("recommender_under_test", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_returns_at_most_limit():
    mod = _load()
    out = mod.run({"budget_total": 1000000, "people": 2, "days": 3, "themes": ["healing"], "limit": 5})
    assert out["agent"] == "travel_recommender_agent"
    assert len(out["recommendations"]) <= 5


def test_within_budget_sorted_first():
    mod = _load()
    out = mod.run({"budget_total": 2000000, "people": 2, "days": 2, "themes": ["culture"]})
    recs = out["recommendations"]
    flags = [r["within_budget"] for r in recs]
    assert flags == sorted(flags, reverse=True)


def test_theme_match_recorded():
    mod = _load()
    out = mod.run({"budget_total": 3000000, "people": 1, "days": 2, "themes": ["culture"],
                   "candidates": ["경주", "부산"]})
    rec_gyeongju = next(r for r in out["recommendations"] if r["destination"] == "경주")
    assert "culture" in rec_gyeongju["matched_themes"]


def test_tiny_budget_marks_over():
    mod = _load()
    out = mod.run({"budget_total": 1000, "people": 2, "days": 3, "themes": []})
    assert all(r["within_budget"] is False for r in out["recommendations"])
