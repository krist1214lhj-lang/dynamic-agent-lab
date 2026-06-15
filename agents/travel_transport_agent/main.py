import json
import os

try:
    import requests
except ImportError:  # pragma: no cover - exercised when dependency is absent
    requests = None


ODsay_API_URL = "https://api.odsay.com/v1/api/searchPubTransPathT"

CITY_COORDINATES = {
    "서울": (126.9780, 37.5665),
    "부산": (129.0756, 35.1796),
    "제주": (126.5312, 33.4996),
    "강릉": (128.8761, 37.7519),
    "대전": (127.3845, 36.3504),
    "대구": (128.6014, 35.8714),
    "광주": (126.8526, 35.1595),
    "인천": (126.7052, 37.4563),
}

PLACEHOLDER_KEYS = {
    "",
    "your_odsay_api_key_here",
    "YOUR_ODSAY_API_KEY",
    "ODSAY_API_KEY",
}


def _get_trip_context(input_data):
    safe_input = input_data if isinstance(input_data, dict) else {}
    origin = safe_input.get("origin", "서울")
    destination = (
        safe_input.get("destination")
        or safe_input.get("location")
        or "부산"
    )
    try:
        days = int(safe_input.get("days", safe_input.get("duration_days", 3)))
    except (TypeError, ValueError):
        days = 3
    travel_style = safe_input.get("travel_style", "대중교통 중심")
    return safe_input, origin, destination, days, travel_style


def _odsay_key():
    return os.getenv("ODSAY_API_KEY") or ""


def _is_valid_odsay_key(service_key):
    return bool(service_key) and service_key not in PLACEHOLDER_KEYS


def _debug_info(service_key="", fallback_reason=None, data_source="mock_fallback"):
    return {
        "env_key_valid": _is_valid_odsay_key(service_key),
        "env_key_length": len(service_key or ""),
        "api_provider": "odsay",
        "fallback_reason": fallback_reason,
        "data_source": data_source,
        "service_key_leaked": False,
    }


def _build_jeju_routes(origin):
    return [
        {
            "title": "항공편",
            "type": "intercity",
            "origin": origin,
            "destination": "제주",
            "mode": "항공편",
            "departure_hint": "김포공항 또는 가까운 출발 공항",
            "arrival_hint": "제주국제공항",
            "estimated_time": "약 1시간 10분~1시간 30분",
            "memo": "가장 일반적이고 빠른 제주 이동 방법",
            "from": origin,
            "to": "제주",
            "method": "항공편",
            "notes": "가장 일반적이고 빠른 제주 이동 방법"
        },
        {
            "title": "선박",
            "type": "intercity",
            "origin": origin,
            "destination": "제주",
            "mode": "선박",
            "departure_hint": "목포, 완도, 여수 등 제주행 여객선 항구",
            "arrival_hint": "제주항 또는 서귀포항",
            "estimated_time": "항구 이동 시간 + 선박 약 3~5시간 이상",
            "memo": "차량 동반이나 느린 여행을 원할 때 선택 가능",
            "from": origin,
            "to": "제주",
            "method": "선박",
            "notes": "차량 동반이나 느린 여행을 원할 때 선택 가능"
        },
        {
            "title": "제주 현지 이동",
            "type": "local",
            "origin": "제주국제공항 또는 제주항",
            "destination": "제주 주요 관광지",
            "mode": "렌터카, 공항버스/시내버스, 택시, 투어버스",
            "departure_hint": "도착 지점",
            "arrival_hint": "숙소 또는 관광지",
            "estimated_time": "권역별 약 20분~1시간 30분",
            "memo": "렌터카는 자유도가 높고, 버스와 투어버스는 운전 부담을 줄일 수 있습니다.",
            "from": "제주국제공항 또는 제주항",
            "to": "제주 주요 관광지",
            "method": "렌터카, 공항버스/시내버스, 택시, 투어버스",
            "notes": "렌터카는 자유도가 높고, 버스와 투어버스는 운전 부담을 줄일 수 있습니다."
        }
    ]


def _build_land_routes(origin, destination):
    return [
        {
            "type": "intercity",
            "from": origin,
            "to": destination,
            "method": "KTX",
            "estimated_time": "약 2시간 30분~3시간",
            "notes": "빠른 이동이 필요한 일정에 적합하며, 주말과 성수기에는 사전 예매를 권장합니다."
        },
        {
            "type": "intercity",
            "from": origin,
            "to": destination,
            "method": "고속버스",
            "estimated_time": "약 3시간 30분~4시간",
            "notes": "철도보다 비용을 낮출 수 있지만 도로 정체에 따라 시간이 달라질 수 있습니다."
        },
        {
            "type": "local",
            "from": f"{destination} 주요 터미널 또는 역",
            "to": f"{destination} 주요 관광지",
            "method": "지하철 또는 시내버스",
            "estimated_time": "약 20~60분",
            "notes": "교통카드를 사용하면 환승이 편리하며, 늦은 시간에는 택시 대안을 함께 고려하세요."
        }
    ]


def _coerce_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _line_name(lane):
    if isinstance(lane, list) and lane:
        first = lane[0] if isinstance(lane[0], dict) else {}
        return first.get("name") or first.get("busNo") or first.get("subwayCode")
    if isinstance(lane, dict):
        return lane.get("name") or lane.get("busNo") or lane.get("subwayCode")
    return None


def _step_summary(step):
    traffic_type = step.get("trafficType")
    section_time = step.get("sectionTime")
    start_name = step.get("startName") or step.get("startStationName")
    end_name = step.get("endName") or step.get("endStationName")
    line_name = _line_name(step.get("lane"))

    if traffic_type == 1:
        label = f"지하철 {line_name}" if line_name else "지하철"
    elif traffic_type == 2:
        label = f"버스 {line_name}" if line_name else "버스"
    elif traffic_type == 3:
        label = "도보"
    else:
        label = "이동"

    parts = [label]
    if start_name or end_name:
        parts.append(f"{start_name or '출발지'} -> {end_name or '도착지'}")
    if section_time is not None:
        parts.append(f"{section_time}분")
    return " · ".join(parts)


def _parse_odsay_routes(payload, origin, destination):
    result = payload.get("result") if isinstance(payload, dict) else None
    paths = result.get("path") if isinstance(result, dict) else None
    if not isinstance(paths, list) or not paths:
        return []

    routes = []
    for index, path in enumerate(paths[:3], start=1):
        if not isinstance(path, dict):
            continue
        info = path.get("info") if isinstance(path.get("info"), dict) else {}
        sub_paths = path.get("subPath") if isinstance(path.get("subPath"), list) else []
        steps = [
            _step_summary(step)
            for step in sub_paths
            if isinstance(step, dict)
        ]
        total_time = _coerce_int(info.get("totalTime"), None)
        payment = _coerce_int(info.get("payment"), None)
        transfer_count = info.get("transferCount")
        if transfer_count is None:
            bus_count = _coerce_int(info.get("busTransitCount"))
            subway_count = _coerce_int(info.get("subwayTransitCount"))
            transfer_count = max(0, bus_count + subway_count - 1)

        route = {
            "route_type": "public_transport",
            "summary": f"대중교통 경로 {index}",
            "total_time_minutes": total_time,
            "payment": payment,
            "transfer_count": _coerce_int(transfer_count),
            "first_start_station": info.get("firstStartStation") or origin,
            "last_end_station": info.get("lastEndStation") or destination,
            "steps_summary": steps[:8],
            "type": "public_transport",
            "from": origin,
            "to": destination,
            "method": "ODsay 대중교통",
            "estimated_time": f"약 {total_time}분" if total_time is not None else "확인 필요",
            "notes": f"환승 {_coerce_int(transfer_count)}회, 예상 요금 {payment}원"
            if payment is not None
            else f"환승 {_coerce_int(transfer_count)}회",
        }
        routes.append(route)
    return routes


def _safe_error(exc):
    return type(exc).__name__


def call_odsay_transport_api(origin, destination, input_data):
    """Call ODsay public transport routing using mapped city coordinates."""
    service_key = _odsay_key()
    origin_coords = CITY_COORDINATES.get(origin)
    destination_coords = CITY_COORDINATES.get(destination)
    if not origin_coords or not destination_coords:
        return None, "missing_coordinates_for_odsay", service_key
    if not _is_valid_odsay_key(service_key):
        return None, "missing_odsay_api_key", service_key
    if requests is None:
        return None, "missing_requests_dependency", service_key

    try:
        params = {
            "apiKey": service_key,
            "SX": origin_coords[0],
            "SY": origin_coords[1],
            "EX": destination_coords[0],
            "EY": destination_coords[1],
            "lang": 0,
        }
        response = requests.get(ODsay_API_URL, params=params, timeout=6)
        if response.status_code >= 400:
            return None, "odsay_http_error", service_key

        try:
            payload = response.json()
        except ValueError:
            return None, "odsay_parse_error", service_key

        if isinstance(payload, dict) and payload.get("error"):
            return None, "odsay_api_error", service_key

        try:
            routes = _parse_odsay_routes(payload, origin, destination)
        except Exception:
            return None, "odsay_parse_error", service_key

        if not routes:
            return None, "odsay_no_route", service_key

        first_route = routes[0]
        total_time = first_route.get("total_time_minutes")
        estimated_time = f"약 {total_time}분" if total_time is not None else "ODsay 경로 결과 참고"
        return {
            "agent": "travel_transport_agent",
            "data_source": "odsay_api",
            "origin": origin,
            "destination": destination,
            "transport_profile": "public_transport",
            "summary": f"{origin}에서 {destination}까지의 ODsay 대중교통 경로를 정리했습니다.",
            "transport_overview": {
                "origin": origin,
                "destination": destination,
                "main_transport": "ODsay 대중교통 길찾기",
                "local_transport": "버스, 지하철, 도보",
                "estimated_travel_time": estimated_time,
            },
            "routes": routes,
            "recommendations": [
                "출발 전 실제 운행 시간과 막차 시간을 다시 확인하세요.",
                "환승 횟수와 도보 구간을 고려해 여유 시간을 확보하세요.",
                "ODsay 결과가 실제 교통 상황과 다를 수 있으므로 현장 안내를 함께 확인하세요.",
            ],
            "transport_tips": [
                "교통카드 또는 모바일 승차권을 미리 준비하세요.",
                "짐이 많다면 환승이 적은 경로를 우선 검토하세요.",
                "비나 폭염이 있으면 도보 구간이 짧은 경로를 선택하세요.",
            ],
            "risks": [
                "ODsay API 결과는 호출 시점 기준이므로 운행 변경이 있을 수 있습니다.",
                "심야 시간대에는 대중교통 경로가 제한될 수 있습니다.",
                "교통 장애, 행사, 공사로 실제 이동 시간이 길어질 수 있습니다.",
            ],
            "next_agents": [
                "travel_schedule_agent",
                "travel_budget_agent",
                "travel_weather_agent",
            ],
            "debug_info": _debug_info(service_key, None, "odsay_api"),
        }, None, service_key
    except requests.exceptions.RequestException:
        return None, "odsay_request_exception", service_key
    except Exception as exc:
        _safe_error(exc)
        return None, "odsay_parse_error", service_key


def _fallback_result(origin, destination, days, travel_style, transport_profile, fallback_reason, data_source):
    is_jeju = transport_profile == "island_air_sea"
    if is_jeju:
        summary = (
            f"{origin}에서 {destination}까지의 이동은 항공편을 우선 추천하고, "
            "선박은 보조 선택지로 정리했습니다."
        )
        main_transport = "항공편 우선, 선박 보조"
        local_transport = "렌터카, 공항버스/시내버스, 택시, 투어버스"
        estimated_travel_time = "항공 약 1시간 10분~1시간 30분, 선박 약 3~5시간 이상"
        routes = _build_jeju_routes(origin)
        transport_tips = [
            "제주는 항공편이 가장 일반적이고 빠른 이동 방법입니다.",
            "렌터카는 동선 자유도가 높지만 성수기에는 사전 예약이 필요합니다.",
            "공항버스/시내버스, 택시, 투어버스를 조합하면 운전 없이도 주요 관광지를 이동할 수 있습니다."
        ]
    else:
        summary = (
            f"{origin}에서 {destination}까지의 도시 간 이동과 "
            f"{destination} 현지 교통을 {days}일 여행 기준 mock 데이터로 정리했습니다."
        )
        main_transport = "KTX 또는 고속버스"
        local_transport = "지하철, 시내버스, 도보, 택시"
        estimated_travel_time = "도시 간 2시간 30분~4시간, 현지 이동 20~60분"
        routes = _build_land_routes(origin, destination)
        transport_tips = [
            f"여행 스타일이 '{travel_style}'이면 도시 간 이동은 시간과 예산을 함께 비교하세요.",
            "열차와 고속버스는 출발 시간대에 따라 가격과 잔여 좌석이 크게 달라질 수 있습니다.",
            "현지 이동은 숙소 위치를 기준으로 지하철역, 버스 정류장, 택시 승강장 접근성을 확인하세요."
        ]

    return {
        "agent": "travel_transport_agent",
        "data_source": data_source,
        "origin": origin,
        "destination": destination,
        "transport_profile": transport_profile,
        "summary": summary,
        "transport_overview": {
            "origin": origin,
            "destination": destination,
            "main_transport": main_transport,
            "local_transport": local_transport,
            "estimated_travel_time": estimated_travel_time
        },
        "routes": routes,
        "transport_tips": transport_tips,
        "recommendations": transport_tips,
        "risks": [
            "현재 결과는 mock 데이터이므로 실제 운행 시간, 요금, 좌석 여부와 다를 수 있습니다.",
            "기상 악화, 도로 정체, 행사 통제로 이동 시간이 길어질 수 있습니다.",
            "심야 이동은 대중교통 운행 종료 시간을 별도로 확인해야 합니다."
        ],
        "next_agents": [
            "travel_schedule_agent",
            "travel_budget_agent",
            "travel_weather_agent"
        ],
        "debug_info": _debug_info(_odsay_key(), fallback_reason, data_source),
    }


def run(input_data):
    """Return ODsay public transit guidance with safe rule/mock fallback."""
    _safe_input, origin, destination, days, travel_style = _get_trip_context(input_data)
    requested_profile = _safe_input.get("transport_profile")
    is_jeju = destination == "제주" or requested_profile == "island_air_sea"
    transport_profile = "island_air_sea" if is_jeju else "public_transport"

    if is_jeju:
        return _fallback_result(
            origin,
            destination,
            days,
            travel_style,
            "island_air_sea",
            "island_air_sea_rule_priority",
            "rule_based_fallback",
        )

    odsay_result, fallback_reason, _service_key = call_odsay_transport_api(
        origin,
        destination,
        _safe_input,
    )
    if odsay_result:
        return odsay_result

    return _fallback_result(
        origin,
        destination,
        days,
        travel_style,
        transport_profile,
        fallback_reason or "odsay_api_error",
        "mock_fallback",
    )


if __name__ == "__main__":
    sample_input = {
        "origin": "서울",
        "destination": "제주",
        "location": "제주",
        "days": 3
    }
    print(json.dumps(run(sample_input), ensure_ascii=False, indent=2))
