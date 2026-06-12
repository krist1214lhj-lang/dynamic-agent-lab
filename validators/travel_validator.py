from copy import deepcopy


JEJU_TRANSPORT_ISSUE = "제주 목적지에 맞지 않는 KTX/고속버스 도시 간 이동 추천이 포함됨"


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


def validate_and_correct(input_data, agent_results):
    corrected_agent_results = []
    validation_report = {
        "status": "ok",
        "issues": [],
        "corrections": [],
    }
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
