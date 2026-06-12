import json


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


def run(input_data):
    """Return mock transport guidance for later public transit or map API wiring."""
    _safe_input, origin, destination, days, travel_style = _get_trip_context(input_data)
    is_jeju = destination == "제주"
    transport_profile = "island_air_sea" if is_jeju else "domestic_land"

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
        "data_source": "mock_fallback",
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
        "debug_info": {
            "origin": origin,
            "destination": destination,
            "transport_profile": transport_profile,
            "used_mock_fallback": True
        }
    }


if __name__ == "__main__":
    sample_input = {
        "origin": "서울",
        "destination": "제주",
        "location": "제주",
        "days": 3
    }
    print(json.dumps(run(sample_input), ensure_ascii=False, indent=2))
