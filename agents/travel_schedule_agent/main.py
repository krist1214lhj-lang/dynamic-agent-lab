import json


OPTIONAL_AGENT_NAMES = [
    "travel_planning_agent",
    "travel_transport_agent",
    "travel_budget_agent",
    "travel_food_agent",
    "travel_event_agent",
    "travel_tour_agent",
    "travel_destination_agent",
    "travel_weather_agent",
]


def _safe_days(value):
    try:
        days = int(value)
    except (TypeError, ValueError):
        days = 3
    return max(days, 1)


def build_duration_strategy(days):
    days = _safe_days(days)
    if days == 1:
        return {
            "days": 1,
            "label": "당일치기",
            "pace": "compact",
            "recommended_tour_count": "1-2",
            "recommended_food_count": "1-2",
            "recommended_event_count": "0-1",
            "night_schedule": False,
            "lodging_required": False,
        }
    if days == 2:
        return {
            "days": 2,
            "label": "1박 2일",
            "pace": "balanced",
            "recommended_tour_count": "2-3",
            "recommended_food_count": "2-3",
            "recommended_event_count": "0-2",
            "night_schedule": True,
            "lodging_required": True,
        }
    return {
        "days": days,
        "label": f"{days - 1}박 {days}일",
        "pace": "relaxed",
        "recommended_tour_count": "3-5",
        "recommended_food_count": "3-5",
        "recommended_event_count": "1-3",
        "night_schedule": True,
        "lodging_required": True,
    }


def _agent_results(input_data):
    results = input_data.get("agent_results")
    if not isinstance(results, list):
        return []
    return [result for result in results if isinstance(result, dict)]


def _result_by_agent(input_data):
    from_map = input_data.get("agent_results_by_agent")
    if isinstance(from_map, dict):
        return {
            key: value
            for key, value in from_map.items()
            if isinstance(value, dict)
        }
    return {
        result.get("agent"): result
        for result in _agent_results(input_data)
        if result.get("agent")
    }


def _readable(value):
    if value in (None, ""):
        return ""
    if isinstance(value, dict):
        for key in ["name", "title", "method", "summary", "description", "label"]:
            if value.get(key):
                return str(value[key])
        return " / ".join(
            str(item_value)
            for item_value in list(value.values())[:2]
            if item_value not in (None, "")
        )
    return str(value)


def _unique_items(items, limit):
    seen = set()
    normalized = []
    for item in items:
        text = _readable(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
        if len(normalized) >= limit:
            break
    return normalized


def _items_from_result(result, keys, limit):
    if not isinstance(result, dict):
        return []
    for key in keys:
        values = result.get(key)
        if isinstance(values, list) and values:
            return _unique_items(values, limit)
    return []


def _food_items(result):
    return _items_from_result(result, ["food_items", "restaurants", "recommendations"], 3)


def _event_items(result):
    return _items_from_result(result, ["event_items", "events", "festival_items", "recommendations"], 2)


def _tour_items(tour_result, destination_result):
    return _unique_items(
        _items_from_result(tour_result, ["tour_items", "attractions", "recommendations"], 4)
        + _items_from_result(destination_result, ["recommendations", "destinations"], 4),
        5,
    )


def _transport_title(origin, destination, transport_result, is_return=False):
    if is_return:
        return f"{destination}에서 {origin}으로 귀가"
    overview = transport_result.get("transport_overview") if isinstance(transport_result, dict) else {}
    main_transport = overview.get("main_transport") if isinstance(overview, dict) else ""
    if main_transport:
        return f"{origin}에서 {destination} 이동 ({main_transport})"
    return f"{origin}에서 {destination}으로 이동"


def _budget_note(budget_result):
    if not isinstance(budget_result, dict):
        return ""
    total = budget_result.get("estimated_total_krw")
    level = budget_result.get("budget_level")
    if isinstance(total, (int, float)) and level:
        return f"예상 예산은 약 {int(total):,}원이며 {level} 기준으로 구성했습니다."
    return ""


def _weather_note(weather_result):
    if not isinstance(weather_result, dict):
        return ""
    weather_text = " ".join(
        _readable(value)
        for value in [
            weather_result.get("summary"),
            weather_result.get("debug_message"),
            weather_result.get("weather_summary"),
            weather_result.get("forecast"),
        ]
        if value
    )
    if any(keyword in weather_text for keyword in ["비", "우천", "강수", "rain"]):
        return "우천 시 실내 관광지 중심으로 조정하세요."
    if any(keyword in weather_text for keyword in ["폭염", "더위", "고온", "heat"]):
        return "폭염이 예상되면 야외 이동 시간을 줄이고 휴식 시간을 확보하세요."
    if any(keyword in weather_text for keyword in ["강풍", "바람", "wind"]):
        return "강풍이 있으면 해변, 전망대, 선박 이동은 현장 상황을 확인하세요."
    return "날씨 정보가 있으면 야외/실내 일정을 당일 조정하세요."


def _block(time, block_type, title, description, source_agent="rule_based_schedule"):
    return {
        "time": time,
        "type": block_type,
        "title": title,
        "description": description,
        "source_agent": source_agent,
    }


def _pick(items, index, fallback):
    if items:
        return items[index % len(items)]
    return fallback


def _day_title(destination, day, days, tour_items):
    if days == 1:
        return f"{destination} 당일 핵심 일정"
    if day == 1:
        return f"{destination} 도착과 핵심 권역 적응 일정"
    if day == days:
        return f"{destination} 여유 일정과 귀가"
    focus = _pick(tour_items, day - 2, "핵심 관광")
    return f"{destination} {focus} 중심 일정"


def _compose_day_trip(origin, destination, context):
    food = context["food_items"]
    event = context["event_items"]
    tour = context["tour_items"]
    transport_result = context["transport_result"]
    afternoon_targets = tour[:2] or event[:1] or [f"{destination} 대표 관광지"]
    return [
        {
            "day": 1,
            "title": _day_title(destination, 1, 1, tour),
            "time_blocks": [
                _block(
                    "오전",
                    "transport",
                    _transport_title(origin, destination, transport_result),
                    "도착 후 핵심 권역으로 바로 이동합니다.",
                    "travel_transport_agent" if transport_result else "rule_based_schedule",
                ),
                _block(
                    "점심",
                    "food",
                    _pick(food, 0, "추천 맛집 방문"),
                    "이동 동선에서 크게 벗어나지 않는 식당을 우선합니다.",
                    "travel_food_agent" if food else "rule_based_schedule",
                ),
                _block(
                    "오후",
                    "tour",
                    " / ".join(afternoon_targets[:2]),
                    "당일치기이므로 관광지는 1~2곳만 압축해서 방문합니다.",
                    "travel_tour_agent" if tour else ("travel_event_agent" if event else "rule_based_schedule"),
                ),
                _block(
                    "귀가",
                    "transport",
                    _transport_title(origin, destination, transport_result, is_return=True),
                    "야간 일정 없이 귀가 교통편에 맞춰 이동합니다.",
                    "travel_transport_agent" if transport_result else "rule_based_schedule",
                ),
            ],
        }
    ]


def _compose_two_day_trip(origin, destination, context):
    food = context["food_items"]
    event = context["event_items"]
    tour = context["tour_items"]
    transport_result = context["transport_result"]
    evening_title = _pick(event, 0, f"{destination} 야간 산책")
    return [
        {
            "day": 1,
            "title": f"{destination} 도착과 오후 관광",
            "time_blocks": [
                _block("오전", "transport", _transport_title(origin, destination, transport_result), "장거리 이동 후 숙소 또는 주요 권역으로 이동합니다.", "travel_transport_agent" if transport_result else "rule_based_schedule"),
                _block("점심", "food", _pick(food, 0, "추천 맛집 방문"), "도착 직후 부담 없는 식사로 일정을 시작합니다.", "travel_food_agent" if food else "rule_based_schedule"),
                _block("오후", "tour", _pick(tour, 0, f"{destination} 주요 관광지"), "숙소 접근성이 좋은 대표 관광지를 먼저 방문합니다.", "travel_tour_agent" if tour else "rule_based_schedule"),
                _block("저녁", "food", _pick(food, 1, "현지 저녁 식사"), "저녁은 숙소 주변 또는 야간 일정 동선에 맞춥니다.", "travel_food_agent" if food else "rule_based_schedule"),
                _block("야간", "event", evening_title, "행사/축제가 있으면 저녁 이후에 배치하고, 없으면 가벼운 산책으로 마무리합니다.", "travel_event_agent" if event else "rule_based_schedule"),
            ],
        },
        {
            "day": 2,
            "title": f"{destination} 오전 관광과 귀가",
            "time_blocks": [
                _block("오전", "tour", _pick(tour, 1, f"{destination} 오전 관광"), "혼잡이 적은 시간에 주요 관광지를 방문합니다.", "travel_tour_agent" if tour else "rule_based_schedule"),
                _block("점심", "food", _pick(food, 2, "마무리 점심"), "귀가 전 마지막 식사를 여유 있게 배치합니다.", "travel_food_agent" if food else "rule_based_schedule"),
                _block("오후", "tour", _pick(event or tour, 1, "기념품 구매와 마무리 산책"), "남은 시간은 짧은 관광 또는 기념품 구매에 사용합니다.", "travel_event_agent" if event else "rule_based_schedule"),
                _block("귀가", "transport", _transport_title(origin, destination, transport_result, is_return=True), "귀가 교통 시간보다 여유 있게 이동합니다.", "travel_transport_agent" if transport_result else "rule_based_schedule"),
            ],
        },
    ]


def _compose_multi_day_trip(origin, destination, days, budget_level, context):
    food = context["food_items"]
    event = context["event_items"]
    tour = context["tour_items"]
    transport_result = context["transport_result"]
    itinerary = []
    for day in range(1, days + 1):
        if day == 1:
            blocks = [
                _block("오전", "transport", _transport_title(origin, destination, transport_result), "장거리 이동 후 숙소 또는 핵심 권역으로 이동합니다.", "travel_transport_agent" if transport_result else "rule_based_schedule"),
                _block("점심", "food", _pick(food, 0, "도착 후 추천 맛집"), "첫 식사는 이동 피로를 고려해 접근성이 좋은 곳으로 잡습니다.", "travel_food_agent" if food else "rule_based_schedule"),
                _block("오후", "tour", _pick(tour, 0, f"{destination} 대표 관광지"), "첫날은 가벼운 대표 관광지 위주로 구성합니다.", "travel_tour_agent" if tour else "rule_based_schedule"),
                _block("저녁", "food", _pick(food, 1, "현지 저녁 식사"), "숙소 주변에서 무리 없는 저녁 일정을 잡습니다.", "travel_food_agent" if food else "rule_based_schedule"),
            ]
        elif day == days:
            blocks = [
                _block("오전", "tour", _pick(tour, day, "카페 또는 산책 코스"), "체크아웃 전후로 부담 없는 여유 일정을 배치합니다.", "travel_tour_agent" if tour else "rule_based_schedule"),
                _block("점심", "food", _pick(food, day, "마지막 점심"), "귀가 전 식사 시간을 충분히 확보합니다.", "travel_food_agent" if food else "rule_based_schedule"),
                _block("오후", "tour", "기념품 구매와 마무리 산책", "남은 시간은 짧은 동선으로 정리합니다.", "rule_based_schedule"),
                _block("귀가", "transport", _transport_title(origin, destination, transport_result, is_return=True), "교통 지연 가능성을 고려해 여유 있게 이동합니다.", "travel_transport_agent" if transport_result else "rule_based_schedule"),
            ]
        else:
            event_title = _pick(event, day - 2, _pick(tour, day, f"{destination} 핵심 관광"))
            blocks = [
                _block("오전", "tour", _pick(tour, day - 1, f"{destination} 오전 관광"), "하루의 핵심 관광지를 오전에 배치합니다.", "travel_tour_agent" if tour else "rule_based_schedule"),
                _block("점심", "food", _pick(food, day - 1, "추천 맛집 방문"), "관광지와 가까운 식당을 우선합니다.", "travel_food_agent" if food else "rule_based_schedule"),
                _block("오후", "tour", _pick(tour, day, f"{destination} 테마 관광"), "지역 또는 테마를 나눠 과밀한 동선을 피합니다.", "travel_tour_agent" if tour else "rule_based_schedule"),
                _block("저녁", "event", event_title, "행사/축제가 있으면 저녁 또는 오후 늦게 배치합니다.", "travel_event_agent" if event else "rule_based_schedule"),
            ]
        itinerary.append({
            "day": day,
            "title": _day_title(destination, day, days, tour),
            "time_blocks": blocks,
        })

    if budget_level == "low":
        itinerary[0]["time_blocks"].append(_block("예산", "budget", "저예산 동선 조정", "유료 관광과 택시 이동을 줄이고 도보/대중교통 중심으로 조정합니다.", "travel_budget_agent"))
    elif budget_level == "high":
        itinerary[0]["time_blocks"].append(_block("예산", "budget", "여유 예산 활용", "식사, 숙박, 이동 편의성을 높이는 방향으로 여유 시간을 확보합니다.", "travel_budget_agent"))
    return itinerary


def _legacy_itinerary(daily_itinerary):
    legacy = []
    for day in daily_itinerary:
        blocks = day.get("time_blocks") or []
        by_time = {block.get("time"): block for block in blocks if isinstance(block, dict)}
        morning = _readable(by_time.get("오전"))
        if not morning and blocks:
            morning = _readable(blocks[0])
        legacy.append({
            "day": day.get("day"),
            "title": day.get("title"),
            "morning": morning,
            "lunch": _readable(by_time.get("점심")),
            "afternoon": _readable(by_time.get("오후")),
            "evening": _readable(by_time.get("저녁") or by_time.get("야간") or by_time.get("귀가")),
        })
    return legacy


def _integration_context(input_data):
    results = _result_by_agent(input_data)
    planning_result = results.get("travel_planning_agent") or {}
    duration_strategy = planning_result.get("duration_strategy") or build_duration_strategy(input_data.get("days"))
    food_result = results.get("travel_food_agent")
    event_result = results.get("travel_event_agent")
    tour_result = results.get("travel_tour_agent")
    destination_result = results.get("travel_destination_agent")
    budget_result = results.get("travel_budget_agent")
    weather_result = results.get("travel_weather_agent")
    transport_result = results.get("travel_transport_agent")
    used_agents = [
        agent_name
        for agent_name in OPTIONAL_AGENT_NAMES
        if agent_name in results
    ]
    missing_optional = [
        agent_name
        for agent_name in OPTIONAL_AGENT_NAMES
        if agent_name not in results
    ]
    return {
        "results": results,
        "duration_strategy": duration_strategy,
        "food_items": _food_items(food_result),
        "event_items": _event_items(event_result),
        "tour_items": _tour_items(tour_result, destination_result),
        "budget_result": budget_result,
        "weather_result": weather_result,
        "transport_result": transport_result,
        "used_agents": used_agents,
        "missing_optional_agents": missing_optional,
    }


def run(input_data):
    """Compose an integrated rule-based itinerary from available agent results."""
    safe_input = input_data if isinstance(input_data, dict) else {}
    destination = safe_input.get("destination") or safe_input.get("location") or "추천 여행지"
    origin = safe_input.get("origin") or "서울"
    days = _safe_days(safe_input.get("days", safe_input.get("duration_days", 3)))
    budget_level = str(safe_input.get("budget_level") or "medium")
    context = _integration_context({**safe_input, "days": days})
    duration_strategy = context["duration_strategy"] or build_duration_strategy(days)

    if days == 1:
        daily_itinerary = _compose_day_trip(origin, destination, context)
    elif days == 2:
        daily_itinerary = _compose_two_day_trip(origin, destination, context)
    else:
        daily_itinerary = _compose_multi_day_trip(origin, destination, days, budget_level, context)

    budget_note = _budget_note(context["budget_result"])
    weather_note = _weather_note(context["weather_result"])
    integration_notes = [
        note
        for note in [
            "다른 에이전트 결과가 있으면 식사, 관광, 행사, 교통 블록에 우선 반영했습니다.",
            budget_note,
            weather_note if context["weather_result"] else "",
        ]
        if note
    ]
    warnings = [
        "실제 영업시간, 예약 가능 여부, 교통 시간은 출발 전 다시 확인하세요.",
        "하루에 너무 많은 장소를 넣지 않도록 핵심 일정 위주로 구성했습니다.",
    ]
    if budget_level == "low":
        warnings.append("저예산 여행은 유료 관광과 택시 이동을 줄이는 방향으로 조정하세요.")
    if weather_note and context["weather_result"]:
        warnings.append(weather_note)

    schedule_summary = f"{destination} {duration_strategy.get('label', f'{days}일')} 일정을 시간대별로 구성했습니다."
    return {
        "agent": "travel_schedule_agent",
        "data_source": "integrated_rule_schedule",
        "destination": destination,
        "origin": origin,
        "days": days,
        "duration_label": duration_strategy.get("label") or build_duration_strategy(days)["label"],
        "duration_strategy": duration_strategy,
        "daily_itinerary": daily_itinerary,
        "itinerary": _legacy_itinerary(daily_itinerary),
        "schedule_summary": schedule_summary,
        "summary": schedule_summary,
        "integration_notes": integration_notes,
        "schedule_tips": integration_notes,
        "warnings": warnings,
        "risks": warnings,
        "next_agents": [
            "travel_budget_agent",
            "travel_transport_agent",
            "travel_tour_agent",
        ],
        "debug_info": {
            "composition_mode": "integrated_rule_schedule",
            "used_agents": context["used_agents"],
            "missing_optional_agents": context["missing_optional_agents"],
            "fallback_reason": None,
        },
    }


if __name__ == "__main__":
    sample_input = {
        "destination": "부산",
        "origin": "서울",
        "days": 3,
        "budget_level": "medium",
        "requested_features": ["schedule"],
    }
    print(json.dumps(run(sample_input), ensure_ascii=False, indent=2))
