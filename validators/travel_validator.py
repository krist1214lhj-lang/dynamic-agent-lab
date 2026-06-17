from copy import deepcopy
from datetime import datetime


JEJU_TRANSPORT_ISSUE = "제주 목적지에 맞지 않는 KTX/고속버스 도시 간 이동 추천이 포함됨"
PAST_EVENT_ISSUE = "이미 종료된 과거 행사가 포함됨"
DUPLICATE_PLACE_ISSUE = "서로 다른 에이전트에서 동일한 장소가 중복 추천됨"


def _destination(input_data):
    return input_data.get("destination") or input_data.get("location")


def _is_intercity_land_route(route):
    if not isinstance(route, dict):
        return False
    if route.get("type") != "intercity":
        return False
    route_text = " ".join(
        str(route.get(key) or "")
        for key in ("title", "mode", "method", "memo", "notes")
    )
    return "KTX" in route_text or "고속버스" in route_text


def _has_invalid_jeju_transport(agent_result):
    if not isinstance(agent_result, dict):
        return False
    if agent_result.get("agent") != "travel_transport_agent":
        return False
    routes = agent_result.get("routes")
    if not isinstance(routes, list):
        return False
    return any(_is_intercity_land_route(route) for route in routes)


def _correct_jeju_transport(input_data, agent_result):
    origin = input_data.get("origin") or "서울"
    corrected = deepcopy(agent_result)
    corrected.update({
        "agent": "travel_transport_agent",
        "summary": f"{origin}에서 제주까지의 이동은 항공편을 우선 추천하고, 선박은 보조 선택지로 정리했습니다.",
        "transport_overview": {
            "origin": origin,
            "destination": "제주",
            "intercity": "항공편 우선, 선박 보조",
            "main_transport": "항공편 우선, 선박 보조",
            "local_transport": "렌터카, 공항버스/시내버스, 택시, 투어버스",
            "estimated_time": "항공 약 1시간 10분~1시간 30분",
            "estimated_travel_time": "항공 약 1시간 10분~1시간 30분",
        },
        "routes": [
            {
                "title": "항공편",
                "type": "intercity",
                "origin": origin,
                "destination": "제주",
                "mode": "항공편",
                "from": origin,
                "to": "제주",
                "method": "항공편",
                "departure_hint": "김포공항 또는 가까운 출발 공항",
                "arrival_hint": "제주국제공항",
                "estimated_time": "약 1시간 10분~1시간 30분",
                "memo": "가장 일반적이고 빠른 제주 이동 방법",
                "notes": "가장 일반적이고 빠른 제주 이동 방법",
            },
            {
                "title": "선박",
                "type": "intercity",
                "origin": origin,
                "destination": "제주",
                "mode": "선박",
                "from": origin,
                "to": "제주",
                "method": "선박",
                "departure_hint": "목포, 완도, 여수 등 제주행 여객선 항구",
                "arrival_hint": "제주항 또는 서귀포항",
                "estimated_time": "항구 이동 시간 + 선박 약 3~5시간 이상",
                "memo": "차량 동반이나 느린 여행을 원할 때 선택 가능",
                "notes": "차량 동반이나 느린 여행을 원할 때 선택 가능",
            },
        ],
    })
    debug_info = dict(corrected.get("debug_info") or {})
    debug_info.update({
        "validator_corrected": True,
        "correction_reason": "jeju_cannot_use_land_only_transport",
        "transport_profile": "island_air_sea",
    })
    corrected["debug_info"] = debug_info
    return corrected


def _filter_past_events(agent_results):
    """오늘 날짜를 기준으로 이미 종료된 이벤트를 필터링합니다."""
    today = datetime.now().strftime("%Y%m%d")
    corrected_results = []
    issues_found = False

    for result in agent_results:
        if result.get("agent") == "travel_event_agent":
            items = result.get("event_items", [])
            valid_items = []
            for item in items:
                end_date = item.get("eventenddate")
                if end_date and str(end_date) < today:
                    issues_found = True
                    continue
                valid_items.append(item)
            
            if issues_found:
                new_result = deepcopy(result)
                new_result["event_items"] = valid_items
                new_result["debug_info"]["validator_filtered_past_events"] = True
                corrected_results.append(new_result)
            else:
                corrected_results.append(result)
        else:
            corrected_results.append(result)
    
    return corrected_results, issues_found


def _deduplicate_places(agent_results):
    """여러 에이전트에서 추천된 중복 장소를 제거합니다."""
    seen_names = set()
    corrected_results = []
    issues_found = False

    # 에이전트 우선순위: tour > event > food
    priority_order = ["travel_tour_agent", "travel_event_agent", "travel_food_agent", "travel_lodging_agent"]
    
    results_map = {r.get("agent"): r for r in agent_results}
    
    for agent_name in priority_order:
        if agent_name not in results_map:
            continue
        
        result = results_map[agent_name]
        items_key = None
        if agent_name == "travel_tour_agent": items_key = "tour_items"
        elif agent_name == "travel_event_agent": items_key = "event_items"
        elif agent_name == "travel_food_agent": items_key = "food_items"
        elif agent_name == "travel_lodging_agent": items_key = "lodging_items"
        
        if items_key and items_key in result:
            items = result[items_key]
            valid_items = []
            for item in items:
                name = item.get("name") or item.get("title")
                if name in seen_names:
                    issues_found = True
                    continue
                seen_names.add(name)
                valid_items.append(item)
            
            if issues_found:
                new_result = deepcopy(result)
                new_result[items_key] = valid_items
                new_result.setdefault("debug_info", {})["validator_deduplicated"] = True
                results_map[agent_name] = new_result

    # 원래 순서대로 다시 조합
    for result in agent_results:
        agent_name = result.get("agent")
        if agent_name in results_map:
            corrected_results.append(results_map[agent_name])
        else:
            corrected_results.append(result)
            
    return corrected_results, issues_found


def validate_and_correct(input_data, agent_results):
    validation_report = {
        "status": "ok",
        "issues": [],
        "corrections": [],
    }
    
    # 1. 과거 이벤트 필터링
    agent_results, has_past_events = _filter_past_events(agent_results)
    if has_past_events:
        validation_report["status"] = "corrected"
        validation_report["issues"].append(PAST_EVENT_ISSUE)
        validation_report["corrections"].append("이미 종료된 과거 행사 데이터를 필터링했습니다.")

    # 2. 중복 장소 제거
    agent_results, has_duplicates = _deduplicate_places(agent_results)
    if has_duplicates:
        validation_report["status"] = "corrected"
        validation_report["issues"].append(DUPLICATE_PLACE_ISSUE)
        validation_report["corrections"].append("서로 다른 추천 항목 간 중복된 장소를 제거했습니다.")

    # 3. 제주도 교통편 보정
    corrected_agent_results = []
    is_jeju = _destination(input_data) == "제주"

    for agent_result in agent_results:
        if is_jeju and _has_invalid_jeju_transport(agent_result):
            corrected_agent_results.append(_correct_jeju_transport(input_data, agent_result))
            validation_report["status"] = "corrected"
            if JEJU_TRANSPORT_ISSUE not in validation_report["issues"]:
                validation_report["issues"].append(JEJU_TRANSPORT_ISSUE)
            validation_report["corrections"].append(
                "travel_transport_agent 결과를 제주 항공편/선박 기준으로 자동 보정했습니다."
            )
        else:
            corrected_agent_results.append(agent_result)

    return corrected_agent_results, validation_report
