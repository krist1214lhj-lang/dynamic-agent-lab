import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_agent():
    p = ROOT / "agents" / "travel_budget_agent" / "main.py"
    spec = importlib.util.spec_from_file_location("budget_agent_under_test", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_budget_agent_returns_formatted_total():
    mod = _load_agent()
    out = mod.run({"origin": "서울", "destination": "부산", "days": 3, "budget_level": "medium"})
    assert out["agent"] == "travel_budget_agent"
    assert out["total"].endswith("원")
    assert out["estimated_budget"]["food"] == "144,000원"


def test_budget_agent_people_scales():
    mod = _load_agent()
    out = mod.run({"origin": "서울", "destination": "부산", "days": 3, "budget_level": "medium", "people": 4})
    assert out["estimated_budget"]["food"] == "576,000원"
