import math

BUDGET_UNIT_PRICES = {
    "low":    {"meal_per_count": 10000, "lodging_per_night": 60000,  "local_transport_per_day": 12000, "tour_event_per_day": 10000, "buffer_rate": 0.08},
    "medium": {"meal_per_count": 18000, "lodging_per_night": 100000, "local_transport_per_day": 20000, "tour_event_per_day": 25000, "buffer_rate": 0.10},
    "high":   {"meal_per_count": 30000, "lodging_per_night": 180000, "local_transport_per_day": 35000, "tour_event_per_day": 50000, "buffer_rate": 0.15},
}

LONG_DISTANCE_TRANSPORT = {
    ("서울", "부산"): {"low": 60000, "medium": 120000, "high": 180000},
    ("서울", "제주"): {"low": 120000, "medium": 220000, "high": 350000},
    ("부산", "제주"): {"low": 100000, "medium": 180000, "high": 300000},
}
DEFAULT_LONG_DISTANCE_TRANSPORT = {"low": 50000, "medium": 90000, "high": 150000}


def _safe_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _round_krw(amount):
    return int(round(float(amount) / 1000) * 1000)


def estimate_budget(origin, destination, days, level, people=1, themes=None, companions=None, priority=None):
    """예상 경비를 정수(원)로 반환. people 기본 1 → 기존 1인 셈법과 동일."""
    themes = themes or []
    companions = companions or []
    level = str(level or "medium").lower()
    if level not in BUDGET_UNIT_PRICES:
        level = "medium"
    people = max(_safe_int(people, 1), 1)
    days = max(_safe_int(days, 1), 1)

    unit = BUDGET_UNIT_PRICES[level].copy()
    if "activity" in themes:
        unit["tour_event_per_day"] *= 1.5
    if "family" in companions:
        unit["buffer_rate"] += 0.05
    if priority == "quality":
        unit["meal_per_count"] *= 1.2

    nights = max(days - 1, 0)
    meal_count = days * 3 - 1 if days > 1 else 2
    rooms = max(people // 2, 1)

    route = (origin, destination)
    long_dist = (LONG_DISTANCE_TRANSPORT.get(route) or DEFAULT_LONG_DISTANCE_TRANSPORT)[level]

    transport = _round_krw((long_dist + unit["local_transport_per_day"] * days) * people)
    lodging = _round_krw(unit["lodging_per_night"] * nights * rooms)
    food = _round_krw(unit["meal_per_count"] * meal_count * people)
    activities = _round_krw(unit["tour_event_per_day"] * days * people)

    subtotal = transport + lodging + food + activities
    buffer = _round_krw(subtotal * unit["buffer_rate"])
    total = _round_krw(subtotal + buffer)

    return {
        "estimated_budget": {
            "transportation": transport,
            "accommodation": lodging,
            "food": food,
            "activities": activities,
            "buffer": buffer,
            "total": total,
        },
        "total": total,
    }
