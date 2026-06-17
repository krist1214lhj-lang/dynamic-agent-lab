import json


BUDGET_UNIT_PRICES = {
    "low": {
        "meal_per_count": 10000,
        "lodging_per_night": 60000,
        "local_transport_per_day": 12000,
        "tour_event_per_day": 10000,
        "buffer_rate": 0.08,
    },
    "medium": {
        "meal_per_count": 18000,
        "lodging_per_night": 100000,
        "local_transport_per_day": 20000,
        "tour_event_per_day": 25000,
        "buffer_rate": 0.10,
    },
    "high": {
        "meal_per_count": 30000,
        "lodging_per_night": 180000,
        "local_transport_per_day": 35000,
        "tour_event_per_day": 50000,
        "buffer_rate": 0.15,
    },
}

LONG_DISTANCE_TRANSPORT = {
    ("서울", "부산"): {"low": 60000, "medium": 120000, "high": 180000},
    ("서울", "제주"): {"low": 120000, "medium": 220000, "high": 350000},
    ("부산", "제주"): {"low": 100000, "medium": 180000, "high": 300000},
}

DEFAULT_LONG_DISTANCE_TRANSPORT = {
    "low": 50000,
    "medium": 90000,
    "high": 150000,
}

def _safe_int(value, default):
    try: return int(value)
    except (TypeError, ValueError): return default

def _round_krw(amount):
    return int(round(float(amount) / 1000) * 1000)

def run(input_data):
    safe_input = input_data if isinstance(input_data, dict) else {}
    destination = safe_input.get("destination") or "부산"
    origin = safe_input.get("origin") or "서울"
    days = max(_safe_int(safe_input.get("days", 3), 3), 1)
    budget_level = str(safe_input.get("budget_level") or "medium").lower()
    if budget_level not in BUDGET_UNIT_PRICES: budget_level = "medium"
    
    # 추가 조건 파싱
    companions = safe_input.get("companions", [])
    themes = safe_input.get("themes", [])
    priority = safe_input.get("priority", "")

    unit = BUDGET_UNIT_PRICES[budget_level].copy()
    
    # 추가 조건에 따른 단가 조정
    if "activity" in themes:
        unit["tour_event_per_day"] *= 1.5 # 액티비티 테마 시 활동비 50% 증액
    if "family" in companions:
        unit["buffer_rate"] += 0.05 # 아이와 함께일 경우 예비비 5% 추가
    if priority == "quality":
        unit["meal_per_count"] *= 1.2 # 퀄리티 중시 시 식비 20% 증액

    lodging_nights = max(days - 1, 0)
    meal_count = days * 3 - 1 if days > 1 else 2

    # 교통비 계산
    route = (origin, destination)
    long_dist = (LONG_DISTANCE_TRANSPORT.get(route) or DEFAULT_LONG_DISTANCE_TRANSPORT)[budget_level]
    local_trans = unit["local_transport_per_day"] * days
    
    transport = _round_krw(long_dist + local_trans)
    lodging = _round_krw(unit["lodging_per_night"] * lodging_nights)
    food = _round_krw(unit["meal_per_count"] * meal_count)
    activities = _round_krw(unit["tour_event_per_day"] * days)

    subtotal = transport + lodging + food + activities
    buffer = _round_krw(subtotal * unit["buffer_rate"])
    total = _round_krw(subtotal + buffer)

    summary = f"{budget_level.upper()} 수준의 예산 설계입니다. "
    if "family" in companions: summary += "아이와 함께하는 여행을 위해 여유로운 예비비를 책정했습니다. "
    if "activity" in themes: summary += "액티비티 중심의 일정을 위해 체험비를 상향 조정했습니다."

    return {
        "agent": "travel_budget_agent",
        "total": f"{total:,}원",
        "summary": summary,
        "estimated_budget": {
            "transportation": f"{transport:,}원",
            "accommodation": f"{lodging:,}원",
            "food": f"{food:,}원",
            "activities": f"{activities:,}원",
            "buffer": f"{buffer:,}원",
            "total": f"{total:,}원"
        },
        "debug_info": { "companions": companions, "themes": themes, "priority": priority }
    }
