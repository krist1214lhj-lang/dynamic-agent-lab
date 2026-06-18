import importlib.util
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def _load():
    spec = importlib.util.spec_from_file_location("schedule_ut", ROOT / "agents" / "travel_schedule_agent" / "main.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def _blocks_day2(pace):
    sch = _load()
    res = sch.run({"destination": "속초", "days": 2, "pace": pace, "themes": []})
    return len(res["daily_itinerary"][1]["time_blocks"])

def test_packed_has_more_blocks_than_relaxed():
    assert _blocks_day2("빡빡") > _blocks_day2("여유")

def test_normal_is_default_three():
    assert _blocks_day2("보통") == 3
