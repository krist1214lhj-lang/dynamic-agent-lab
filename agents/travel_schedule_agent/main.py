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
    "travel_lodging_agent",
]


def _safe_days(value):
    try:
        days = int(value)
    except (TypeError, ValueError):
        days = 3
    return max(days, 1)


def build_duration_strategy(days, priority):
    days = _safe_days(days)
    pace = "balanced"
    if priority == "distance": pace = "compact"
    elif priority == "quality": pace = "relaxed"
    
    if days == 1:
        return {
            "days": 1,
            "label": "당일치기",
            "pace": pace if pace != "relaxed" else "balanced",
            "recommended_tour_count": "1-2",
            "recommended_food_count": "1-2",
            "recommended_event_count": "0-1",
            "night_schedule": False,
            "lodging_required": False,
        }
    return {
        "days": days,
        "label": f"{days - 1}박 {days}일",
        "pace": pace,
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
        return {key: value for key, value in from_map.items() if isinstance(value, dict)}
    return {result.get("agent"): result for result in _agent_results(input_data) if result.get("agent")}


def _readable(value):
    if value in (None, ""): return ""
    if isinstance(value, dict):
        for key in ["name", "title", "summary"]:
            if value.get(key): return str(value[key])
        return str(list(value.values())[0])
    return str(value)


def _items_from_result(result, keys, limit):
    if not isinstance(result, dict): return []
    for key in keys:
        values = result.get(key)
        if isinstance(values, list) and values:
            return [_readable(v) for v in values[:limit]]
    return []


def _block(time, block_type, title, description, source_agent="rule_based_schedule"):
    return {"time": time, "type": block_type, "title": title, "description": description, "source_agent": source_agent}


def _pick(items, index, fallback):
    if items: return items[index % len(items)]
    return fallback


def run(input_data):
    safe_input = input_data if isinstance(input_data, dict) else {}
    destination = safe_input.get("destination") or "추천 여행지"
    origin = safe_input.get("origin") or "서울"
    days = _safe_days(safe_input.get("days", 3))
    
    # 추가 조건 추출
    companions = safe_input.get("companions", [])
    themes = safe_input.get("themes", [])
    priority = safe_input.get("priority", "")
    
    results = _result_by_agent(input_data)
    food = _items_from_result(results.get("travel_food_agent"), ["food_items"], 5)
    tour = _items_from_result(results.get("travel_tour_agent"), ["tour_items"], 5)
    
    strategy = build_duration_strategy(days, priority)
    
    daily_itinerary = []
    for d in range(1, days + 1):
        blocks = []
        if d == 1:
            blocks.append(_block("오전", "transport", f"{origin}에서 출발", f"{destination} 주요 지역으로 이동합니다."))
            blocks.append(_block("점심", "food", _pick(food, 0, "로컬 맛집"), "도착 후 첫 식사입니다."))
            blocks.append(_block("오후", "tour", _pick(tour, 0, "핵심 명소"), "가장 가보고 싶었던 장소를 방문합니다."))
        else:
            blocks.append(_block("오전", "tour", _pick(tour, d, "오전 산책/관광"), "여유로운 오전 일정을 시작합니다."))
            blocks.append(_block("점심", "food", _pick(food, d, "추천 식당"), "근처 맛집에서 점심을 해결합니다."))
            blocks.append(_block("오후", "tour", _pick(tour, d+1, "테마 관광"), f"{', '.join(themes)} 테마에 맞춘 일정을 즐깁니다."))
        
        daily_itinerary.append({
            "day": d,
            "title": f"{destination} {d}일차 일정",
            "time_blocks": blocks
        })

    summary = f"{destination} {days}일 맞춤형 일정입니다. "
    if companions: summary += f"{', '.join(companions)} 동행에 맞춘 페이스로 구성했습니다. "
    if themes: summary += f"{', '.join(themes)} 테마를 중심으로 설계되었습니다."

    return {
        "agent": "travel_schedule_agent",
        "destination": destination,
        "summary": summary,
        "daily_itinerary": daily_itinerary,
        "duration_strategy": strategy,
        "debug_info": {
            "companions": companions,
            "themes": themes,
            "priority": priority
        }
    }

if __name__ == "__main__":
    print(json.dumps(run({"destination": "제주", "days": 2, "companions": ["family"], "themes": ["healing"]}), ensure_ascii=False, indent=2))
