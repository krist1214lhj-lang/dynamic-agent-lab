import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from budget_model import estimate_budget


def run(input_data):
    safe_input = input_data if isinstance(input_data, dict) else {}
    destination = safe_input.get("destination") or "부산"
    origin = safe_input.get("origin") or "서울"
    days = safe_input.get("days", 3)
    budget_level = str(safe_input.get("budget_level") or "medium").lower()
    people = safe_input.get("people", 1)

    companions = safe_input.get("companions", [])
    themes = safe_input.get("themes", [])
    priority = safe_input.get("priority", "")

    result = estimate_budget(origin, destination, days, budget_level,
                             people=people, themes=themes, companions=companions, priority=priority)
    eb = result["estimated_budget"]
    total = result["total"]

    summary = f"{budget_level.upper()} 수준의 예산 설계입니다. "
    if "family" in companions:
        summary += "아이와 함께하는 여행을 위해 여유로운 예비비를 책정했습니다. "
    if "activity" in themes:
        summary += "액티비티 중심의 일정을 위해 체험비를 상향 조정했습니다."

    return {
        "agent": "travel_budget_agent",
        "data_source": "mock_plus_conditions",
        "total": f"{total:,}원",
        "summary": summary,
        "estimated_budget": {
            "transportation": f"{eb['transportation']:,}원",
            "accommodation": f"{eb['accommodation']:,}원",
            "food": f"{eb['food']:,}원",
            "activities": f"{eb['activities']:,}원",
            "buffer": f"{eb['buffer']:,}원",
            "total": f"{eb['total']:,}원",
        },
        "debug_info": {"companions": companions, "themes": themes, "priority": priority},
    }
