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

BUDGET_SUMMARY = {
    "low": "저예산 중심으로 교통비와 숙박비를 줄이는 방향의 예산입니다.",
    "medium": "일반적인 국내여행 기준으로 무리 없는 표준 예산입니다.",
    "high": "숙박, 식사, 이동 편의성을 높인 여유 예산입니다.",
}

DURATION_LABELS = {
    1: "당일치기",
    2: "1박 2일",
    3: "2박 3일",
    4: "3박 4일",
    5: "4박 5일",
}


def _safe_input(input_data):
    return input_data if isinstance(input_data, dict) else {}


def _safe_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _round_krw(amount):
    return int(round(float(amount) / 1000) * 1000)


def _duration_label(days):
    if days in DURATION_LABELS:
        return DURATION_LABELS[days]
    if days <= 1:
        return "당일치기"
    return f"{days - 1}박 {days}일"


def _normalize_budget_level(value):
    budget_level = str(value or "medium").strip().lower()
    if budget_level not in BUDGET_UNIT_PRICES:
        return "medium"
    return budget_level


def _long_distance_transport(origin, destination, budget_level):
    route = (origin, destination)
    reverse_route = (destination, origin)
    table = (
        LONG_DISTANCE_TRANSPORT.get(route)
        or LONG_DISTANCE_TRANSPORT.get(reverse_route)
        or DEFAULT_LONG_DISTANCE_TRANSPORT
    )
    return table[budget_level]


def _meal_count(days):
    if days <= 1:
        return 2
    return days * 3 - 1


def _assumptions(days, origin, destination, budget_level, requested_features):
    assumptions = [
        "1인 기준 국내여행 예상 예산입니다.",
        "교통비는 왕복 장거리 이동과 현지 이동을 합산했습니다.",
        "식비는 일반 식사 중심으로 계산했습니다.",
    ]
    if days <= 1:
        assumptions.append("당일치기이므로 숙박비는 제외했습니다.")
    if origin == destination:
        assumptions.append("출발지와 목적지가 같아도 기본 현지 이동비는 포함했습니다.")
    if "event" in requested_features or "tour" in requested_features:
        assumptions.append("관광/행사 선택에 따른 활동비를 일 단위로 포함했습니다.")
    if "lodging" in requested_features:
        assumptions.append("숙박 추천 기능이 선택되어 숙박비 항목을 별도로 반영했습니다.")
    assumptions.append(f"예산 수준은 {budget_level} 단가표를 적용했습니다.")
    return assumptions


def _saving_tips(budget_level, lodging_required):
    tips = [
        "교통편은 출발 시간대별 가격을 비교해 예약하세요.",
        "관광지 입장권과 지역 패스를 묶어서 비교하면 활동비를 줄일 수 있습니다.",
    ]
    if budget_level == "low":
        tips.insert(0, "숙소는 역세권보다 한두 정거장 떨어진 지역을 함께 비교하세요.")
    elif budget_level == "medium":
        tips.insert(0, "숙소 위치와 교통비를 함께 비교하면 총액을 안정적으로 관리할 수 있습니다.")
    else:
        tips.insert(0, "프리미엄 숙소나 택시 이동은 예비비 안에서 우선순위를 정하세요.")
    if not lodging_required:
        tips.append("당일치기는 식사 시간과 귀가 교통편을 먼저 고정하면 지출 변동이 줄어듭니다.")
    return tips


def _warnings(destination, budget_level, lodging_required):
    warnings = [
        "성수기, 주말, 연휴에는 교통비와 숙박비가 상승할 수 있습니다.",
        "실제 지출은 예약 시점, 동선, 개인 소비 성향에 따라 달라질 수 있습니다.",
    ]
    if destination == "제주":
        warnings.append("제주는 항공권과 렌터카 가격 변동이 커서 사전 확인이 필요합니다.")
    if budget_level == "low" and lodging_required:
        warnings.append("저예산 숙박은 위치와 후기, 취소 규정을 함께 확인하세요.")
    return warnings


def _legacy_estimated_budget(breakdown, total):
    return {
        "transportation": f"{breakdown['transport']:,}원",
        "accommodation": f"{breakdown['lodging']:,}원",
        "food": f"{breakdown['food']:,}원",
        "activities": f"{breakdown['tour_event']:,}원",
        "buffer": f"{breakdown['buffer']:,}원",
        "total": f"{total:,}원",
    }


def run(input_data):
    """Calculate a deterministic rule-based domestic travel budget."""
    safe_input = _safe_input(input_data)
    destination = safe_input.get("destination") or safe_input.get("location") or "Unknown destination"
    origin = safe_input.get("origin") or "서울"
    days = max(_safe_int(safe_input.get("days", safe_input.get("duration_days", 3)), 3), 1)
    budget_level = _normalize_budget_level(safe_input.get("budget_level", "medium"))
    requested_features = safe_input.get("requested_features") or []
    if not isinstance(requested_features, list):
        requested_features = []

    unit_prices = BUDGET_UNIT_PRICES[budget_level]
    duration_label = _duration_label(days)
    lodging_required = days >= 2
    lodging_nights = max(days - 1, 0)
    meal_count = _meal_count(days)

    long_distance = _round_krw(_long_distance_transport(origin, destination, budget_level))
    local_transport = _round_krw(unit_prices["local_transport_per_day"] * days)
    transport = _round_krw(long_distance + local_transport)
    lodging = _round_krw(unit_prices["lodging_per_night"] * lodging_nights)
    food = _round_krw(unit_prices["meal_per_count"] * meal_count)
    tour_event = _round_krw(unit_prices["tour_event_per_day"] * days)

    subtotal = transport + lodging + food + tour_event
    buffer = _round_krw(subtotal * unit_prices["buffer_rate"])
    estimated_total = _round_krw(subtotal + buffer)

    budget_breakdown = {
        "long_distance_transport": long_distance,
        "local_transport": local_transport,
        "transport": transport,
        "lodging": lodging,
        "food": food,
        "tour_event": tour_event,
        "buffer": buffer,
    }

    summary = BUDGET_SUMMARY[budget_level]
    return {
        "agent": "travel_budget_agent",
        "data_source": "rule_based_budget",
        "destination": destination,
        "origin": origin,
        "days": days,
        "duration_label": duration_label,
        "budget_level": budget_level,
        "lodging_required": lodging_required,
        "lodging_nights": lodging_nights,
        "meal_count": meal_count,
        "estimated_total_krw": estimated_total,
        "budget_breakdown": budget_breakdown,
        "summary": summary,
        "assumptions": _assumptions(days, origin, destination, budget_level, requested_features),
        "saving_tips": _saving_tips(budget_level, lodging_required),
        "warnings": _warnings(destination, budget_level, lodging_required),
        "risks": _warnings(destination, budget_level, lodging_required),
        "estimated_budget": _legacy_estimated_budget(budget_breakdown, estimated_total),
        "next_agents": [
            "travel_schedule_agent",
            "travel_transport_agent",
            "travel_tour_agent",
        ],
        "debug_info": {
            "calculation_mode": "rule_based_budget",
            "api_provider": None,
            "fallback_reason": None,
        },
    }


if __name__ == "__main__":
    sample_input = {
        "destination": "부산",
        "location": "부산",
        "origin": "서울",
        "days": 3,
        "budget_level": "medium",
        "requested_features": ["budget"],
    }
    print(json.dumps(run(sample_input), ensure_ascii=False, indent=2))
