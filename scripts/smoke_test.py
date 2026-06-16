# Run from the project root:
# python scripts/smoke_test.py

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


BASE_URL = os.environ.get("BASE_URL", "http://localhost:8013")

EXPECTED_AGENTS = {
    "travel_planning_agent",
    "travel_destination_agent",
    "travel_budget_agent",
    "travel_schedule_agent",
    "travel_weather_agent",
    "travel_tour_agent",
    "travel_food_agent",
    "travel_event_agent",
    "travel_transport_agent",
    "travel_lodging_agent",
}

EXPECTED_FEATURE_MAP = {
    "destination": "travel_destination_agent",
    "budget": "travel_budget_agent",
    "schedule": "travel_schedule_agent",
    "weather": "travel_weather_agent",
    "tour": "travel_tour_agent",
    "transport": "travel_transport_agent",
    "food": "travel_food_agent",
    "event": "travel_event_agent",
    "planning": "travel_planning_agent",
    "lodging": "travel_lodging_agent",
}


class SmokeTestError(Exception):
    pass


def request_json(method, path, payload=None):
    url = f"{BASE_URL}{path}"
    body = None
    headers = {"Accept": "application/json"}

    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise SmokeTestError(f"HTTP {exc.code}: {raw}") from exc
    except urllib.error.URLError as exc:
        raise SmokeTestError(
            f"서버가 실행 중인지 확인하세요: {BASE_URL} ({exc.reason})"
        ) from exc
    except TimeoutError as exc:
        raise SmokeTestError(f"요청 시간이 초과되었습니다: {url}") from exc
    except json.JSONDecodeError as exc:
        raise SmokeTestError(f"JSON 응답을 파싱할 수 없습니다: {url}") from exc


def find_agent_result(data, agent_name):
    for result in data.get("agent_results", []):
        if result.get("agent") == agent_name:
            return result
    return None


def text_in_route(route, keyword):
    searchable = [
        route.get("title"),
        route.get("type"),
        route.get("method"),
        route.get("mode"),
        route.get("from"),
        route.get("to"),
        route.get("origin"),
        route.get("destination"),
        route.get("notes"),
        route.get("memo"),
    ]
    return any(keyword in str(value) for value in searchable if value is not None)


def first_intercity_route(routes):
    for route in routes:
        if route.get("type") == "intercity":
            return route
    return routes[0] if routes else {}


def assert_true(condition, reason):
    if not condition:
        raise SmokeTestError(reason)


def assert_planning_auto_included(data):
    selected_agents = data.get("selected_agents", [])
    loaded_agents = data.get("loaded_agents", [])

    assert_true(
        selected_agents and selected_agents[0] == "travel_planning_agent",
        "selected_agents 첫 번째가 travel_planning_agent가 아닙니다.",
    )
    assert_true(
        any(agent.get("name") == "travel_planning_agent" for agent in loaded_agents),
        "loaded_agents에 travel_planning_agent가 없습니다.",
    )


def local_env_value(name):
    value = os.environ.get(name)
    if value:
        return value

    env_path = Path(".env")
    if not env_path.exists():
        return ""

    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, raw_value = stripped.split("=", 1)
            if key.strip() == name:
                return raw_value.strip().strip("\"'")
    except OSError:
        return ""
    return ""


def assert_known_api_keys_not_leaked(data):
    serialized = json.dumps(data, ensure_ascii=False)
    for env_name in ["KMA_SERVICE_KEY", "TOUR_API_SERVICE_KEY", "ODSAY_API_KEY"]:
        env_value = local_env_value(env_name)
        if env_value:
            assert_true(
                env_value not in serialized,
                f"{env_name} 원문이 응답에 노출되었습니다.",
            )


def test_agent_library():
    data = request_json("GET", "/agent-library")
    agent_names = {agent.get("name") for agent in data.get("agents", [])}

    assert_true(
        data.get("total_agents", 0) >= len(EXPECTED_AGENTS),
        f"total_agents가 {len(EXPECTED_AGENTS)}보다 작습니다.",
    )
    assert_true(
        data.get("available_count", 0) >= len(EXPECTED_AGENTS),
        f"available_count가 {len(EXPECTED_AGENTS)}보다 작습니다.",
    )
    missing = sorted(EXPECTED_AGENTS - agent_names)
    assert_true(not missing, f"누락된 에이전트: {', '.join(missing)}")


def test_health():
    data = request_json("GET", "/health")

    assert_true(data.get("status") == "ok", "health status가 ok가 아닙니다.")
    assert_true(
        data.get("available_agents", 0) >= len(EXPECTED_AGENTS),
        f"available_agents가 {len(EXPECTED_AGENTS)}보다 작습니다.",
    )


def test_feature_map():
    data = request_json("GET", "/feature-map")
    features = data.get("features") or {}

    for feature, expected_agent in EXPECTED_FEATURE_MAP.items():
        assert_true(
            features.get(feature) == expected_agent,
            f"{feature} feature가 {expected_agent}로 매핑되지 않았습니다.",
        )

    assert_true(
        data.get("feature_count", 0) >= len(EXPECTED_FEATURE_MAP),
        f"feature_count가 {len(EXPECTED_FEATURE_MAP)}보다 작습니다.",
    )


def test_jeju_weather():
    payload = {
        "user_request": "",
        "destination": "제주",
        "location": "제주",
        "origin": "서울",
        "days": 3,
        "budget_level": "medium",
        "requested_features": ["weather"],
    }
    data = request_json("POST", "/run-workflow", payload)
    weather_result = find_agent_result(data, "travel_weather_agent")
    assert_planning_auto_included(data)

    assert_true(
        "travel_weather_agent" in data.get("selected_agents", []),
        "selected_agents에 travel_weather_agent가 없습니다.",
    )
    assert_true(
        data.get("input_data_summary", {}).get("destination") == "제주",
        "input_data_summary.destination이 제주가 아닙니다.",
    )
    assert_true(weather_result is not None, "travel_weather_agent 결과가 없습니다.")
    assert_true(
        weather_result.get("location") == "제주",
        "travel_weather_agent location이 제주가 아닙니다.",
    )

    forecast = weather_result.get("forecast") or {}
    weather_summary = weather_result.get("weather_summary") or {}
    has_temperature_or_condition = bool(
        forecast.get("temperature")
        or forecast.get("condition")
        or weather_summary.get("temperature")
        or weather_summary.get("condition")
    )
    assert_true(
        has_temperature_or_condition,
        "forecast 또는 weather_summary에 temperature/condition 값이 없습니다.",
    )


def test_jeju_transport():
    payload = {
        "user_request": "",
        "destination": "제주",
        "location": "제주",
        "origin": "서울",
        "days": 3,
        "budget_level": "medium",
        "requested_features": ["transport"],
    }
    data = request_json("POST", "/run-workflow", payload)
    transport_result = find_agent_result(data, "travel_transport_agent")
    assert_planning_auto_included(data)

    assert_true(
        "travel_transport_agent" in data.get("selected_agents", []),
        "selected_agents에 travel_transport_agent가 없습니다.",
    )
    assert_true(
        data.get("input_data_summary", {}).get("destination") == "제주",
        "input_data_summary.destination이 제주가 아닙니다.",
    )
    assert_true(transport_result is not None, "travel_transport_agent 결과가 없습니다.")
    assert_true(
        transport_result.get("transport_profile") == "island_air_sea",
        "제주 교통 transport_profile이 island_air_sea가 아닙니다.",
    )
    debug_info = transport_result.get("debug_info") or {}
    fallback_reason = debug_info.get("fallback_reason")
    if fallback_reason:
        assert_true(
            fallback_reason in {
                "island_air_sea_rule_priority",
                "missing_odsay_api_key",
                "missing_coordinates_for_odsay",
                "odsay_http_error",
                "odsay_api_error",
                "odsay_parse_error",
                "odsay_no_route",
                "odsay_request_exception",
                "missing_requests_dependency",
            },
            f"제주 교통 fallback_reason이 명확하지 않습니다: {fallback_reason}",
        )

    routes = transport_result.get("routes") or []
    assert_true(
        any(text_in_route(route, "항공편") for route in routes),
        "routes에 항공편이 없습니다.",
    )
    assert_true(
        any(text_in_route(route, "선박") for route in routes),
        "routes에 선박이 없습니다.",
    )

    first_route = first_intercity_route(routes)
    assert_true(
        not text_in_route(first_route, "KTX"),
        "제주 도시 간 이동 추천 1순위가 KTX입니다.",
    )
    assert_true(
        data.get("validation_report") is not None,
        "validation_report가 없습니다.",
    )


def test_seoul_busan_transport():
    payload = {
        "user_request": "",
        "destination": "부산",
        "location": "부산",
        "origin": "서울",
        "days": 2,
        "budget_level": "medium",
        "requested_features": ["transport"],
    }
    data = request_json("POST", "/run-workflow", payload)
    transport_result = find_agent_result(data, "travel_transport_agent")
    assert_planning_auto_included(data)

    assert_true(
        "travel_transport_agent" in data.get("selected_agents", []),
        "selected_agents에 travel_transport_agent가 없습니다.",
    )
    assert_true(transport_result is not None, "travel_transport_agent 결과가 없습니다.")

    data_source = transport_result.get("data_source")
    assert_true(
        data_source in {"odsay_api", "mock_fallback", "rule_based_fallback"},
        f"transport data_source가 허용되지 않은 값입니다: {data_source}",
    )

    debug_info = transport_result.get("debug_info") or {}
    if data_source in {"mock_fallback", "rule_based_fallback"}:
        assert_true(
            bool(debug_info.get("fallback_reason")),
            "fallback data_source인데 debug_info.fallback_reason이 없습니다.",
        )

    assert_true(
        debug_info.get("service_key_leaked") is False,
        "debug_info.service_key_leaked가 false가 아닙니다.",
    )
    assert_true(
        "api_provider" not in debug_info or debug_info.get("api_provider") == "odsay",
        "debug_info.api_provider가 odsay가 아닙니다.",
    )

    odsay_key = local_env_value("ODSAY_API_KEY")
    if odsay_key:
        serialized = json.dumps(data, ensure_ascii=False)
        assert_true(
            odsay_key not in serialized,
            "ODSay API 키 원문이 응답에 노출되었습니다.",
        )


def test_busan_destination():
    payload = {
        "user_request": "",
        "destination": "부산",
        "location": "부산",
        "origin": "서울",
        "days": 3,
        "budget_level": "medium",
        "requested_features": ["destination"],
    }
    data = request_json("POST", "/run-workflow", payload)
    destination_result = find_agent_result(data, "travel_destination_agent")
    assert_planning_auto_included(data)

    assert_true(
        "travel_destination_agent" in data.get("selected_agents", []),
        "selected_agents에 travel_destination_agent가 없습니다.",
    )
    assert_true(
        any(agent.get("name") == "travel_destination_agent" for agent in data.get("loaded_agents", [])),
        "loaded_agents에 travel_destination_agent가 없습니다.",
    )
    assert_true(destination_result is not None, "travel_destination_agent 결과가 없습니다.")

    data_source = destination_result.get("data_source")
    assert_true(
        data_source in {"tour_api", "mock_fallback", "rule_based_fallback"},
        f"destination data_source가 허용되지 않은 값입니다: {data_source}",
    )
    recommendations = destination_result.get("recommendations") or destination_result.get("destinations") or []
    assert_true(bool(recommendations), "destination 추천 목록이 없습니다.")

    debug_info = destination_result.get("debug_info") or {}
    if data_source in {"mock_fallback", "rule_based_fallback"}:
        assert_true(
            bool(debug_info.get("fallback_reason")),
            "fallback data_source인데 debug_info.fallback_reason이 없습니다.",
        )
    assert_true(
        debug_info.get("service_key_leaked") is False,
        "debug_info.service_key_leaked가 false가 아닙니다.",
    )
    assert_true(
        "api_provider" not in debug_info or debug_info.get("api_provider") == "tour_api",
        "debug_info.api_provider가 tour_api가 아닙니다.",
    )

    tour_key = local_env_value("TOUR_API_SERVICE_KEY")
    if tour_key:
        serialized = json.dumps(data, ensure_ascii=False)
        assert_true(
            tour_key not in serialized,
            "TourAPI 키 원문이 응답에 노출되었습니다.",
        )


def test_busan_budget():
    payload = {
        "user_request": "",
        "destination": "부산",
        "location": "부산",
        "origin": "서울",
        "days": 3,
        "budget_level": "medium",
        "requested_features": ["budget"],
    }
    data = request_json("POST", "/run-workflow", payload)
    budget_result = find_agent_result(data, "travel_budget_agent")
    assert_planning_auto_included(data)

    assert_true(
        "travel_budget_agent" in data.get("selected_agents", []),
        "selected_agents에 travel_budget_agent가 없습니다.",
    )
    assert_true(
        any(agent.get("name") == "travel_budget_agent" for agent in data.get("loaded_agents", [])),
        "loaded_agents에 travel_budget_agent가 없습니다.",
    )
    assert_true(budget_result is not None, "travel_budget_agent 결과가 없습니다.")
    assert_true(
        budget_result.get("data_source") == "rule_based_budget",
        "budget data_source가 rule_based_budget이 아닙니다.",
    )
    assert_true(
        budget_result.get("estimated_total_krw", 0) > 0,
        "estimated_total_krw가 0보다 크지 않습니다.",
    )

    breakdown = budget_result.get("budget_breakdown") or {}
    assert_true(breakdown.get("transport", 0) > 0, "budget_breakdown.transport가 없습니다.")
    assert_true(breakdown.get("food", 0) > 0, "budget_breakdown.food가 없습니다.")
    assert_true(
        budget_result.get("duration_label") == "2박 3일",
        "duration_label이 2박 3일이 아닙니다.",
    )
    assert_true(
        budget_result.get("lodging_required") is True,
        "lodging_required가 true가 아닙니다.",
    )
    assert_known_api_keys_not_leaked(data)


def test_busan_integrated_schedule():
    payload = {
        "user_request": "",
        "destination": "부산",
        "location": "부산",
        "origin": "서울",
        "days": 3,
        "budget_level": "medium",
        "requested_features": ["schedule", "transport", "budget", "food", "event", "tour"],
    }
    data = request_json("POST", "/run-workflow", payload)
    selected_agents = data.get("selected_agents", [])
    schedule_result = find_agent_result(data, "travel_schedule_agent")
    assert_planning_auto_included(data)

    for agent_name in [
        "travel_schedule_agent",
        "travel_transport_agent",
        "travel_budget_agent",
        "travel_food_agent",
        "travel_event_agent",
        "travel_tour_agent",
    ]:
        assert_true(agent_name in selected_agents, f"selected_agents에 {agent_name}가 없습니다.")

    assert_true(schedule_result is not None, "travel_schedule_agent 결과가 없습니다.")
    assert_true(
        schedule_result.get("data_source") in {"integrated_rule_schedule", "rule_based_schedule", "mock_fallback"},
        "schedule data_source가 허용된 값이 아닙니다.",
    )

    daily_itinerary = schedule_result.get("daily_itinerary")
    assert_true(isinstance(daily_itinerary, list), "daily_itinerary가 배열이 아닙니다.")
    assert_true(len(daily_itinerary) == payload["days"], "daily_itinerary 길이가 여행 일수와 다릅니다.")
    for day in daily_itinerary:
        assert_true(isinstance(day.get("time_blocks"), list), "time_blocks가 배열이 아닙니다.")

    assert_true(bool(schedule_result.get("schedule_summary")), "schedule_summary가 없습니다.")
    duration_strategy = schedule_result.get("duration_strategy") or {}
    assert_true(
        duration_strategy.get("label") == "2박 3일",
        "duration_strategy.label이 2박 3일이 아닙니다.",
    )
    assert_known_api_keys_not_leaked(data)


def test_jeju_food():
    payload = {
        "user_request": "",
        "destination": "제주",
        "location": "제주",
        "origin": "서울",
        "days": 3,
        "budget_level": "low",
        "requested_features": ["food"],
    }
    data = request_json("POST", "/run-workflow", payload)
    food_result = find_agent_result(data, "travel_food_agent")
    routing_debug = data.get("routing_debug") or {}
    assert_planning_auto_included(data)

    assert_true(
        "travel_food_agent" in data.get("selected_agents", []),
        "selected_agents에 travel_food_agent가 없습니다.",
    )
    assert_true(
        any(agent.get("name") == "travel_food_agent" for agent in data.get("loaded_agents", [])),
        "loaded_agents에 travel_food_agent가 없습니다.",
    )
    assert_true(food_result is not None, "travel_food_agent 결과가 없습니다.")
    assert_true(
        data.get("input_data_summary", {}).get("destination") == "제주",
        "input_data_summary.destination이 제주가 아닙니다.",
    )

    food_items = food_result.get("food_items") or []
    assert_true(food_items, "food_items가 없습니다.")
    assert_true(len(food_items) >= 3, "food_items가 3개보다 작습니다.")
    assert_true(
        "travel_food_agent" in (routing_debug.get("selected_agents_from_features") or []),
        "routing_debug.selected_agents_from_features에 travel_food_agent가 없습니다.",
    )
    assert_true(
        "travel_planning_agent" in (routing_debug.get("auto_included_agents") or []),
        "routing_debug.auto_included_agents에 travel_planning_agent가 없습니다.",
    )


def test_jeju_event():
    payload = {
        "user_request": "",
        "destination": "제주",
        "location": "제주",
        "origin": "서울",
        "days": 3,
        "budget_level": "low",
        "requested_features": ["event"],
    }
    data = request_json("POST", "/run-workflow", payload)
    event_result = find_agent_result(data, "travel_event_agent")
    routing_debug = data.get("routing_debug") or {}
    assert_planning_auto_included(data)

    assert_true(
        "travel_event_agent" in data.get("selected_agents", []),
        "selected_agents에 travel_event_agent가 없습니다.",
    )
    assert_true(
        any(agent.get("name") == "travel_event_agent" for agent in data.get("loaded_agents", [])),
        "loaded_agents에 travel_event_agent가 없습니다.",
    )
    assert_true(event_result is not None, "travel_event_agent 결과가 없습니다.")
    assert_true(
        data.get("input_data_summary", {}).get("destination") == "제주",
        "input_data_summary.destination이 제주가 아닙니다.",
    )

    event_items = event_result.get("event_items") or []
    assert_true(event_items, "event_items가 없습니다.")
    assert_true(len(event_items) >= 3, "event_items가 3개보다 작습니다.")
    assert_true(
        "travel_event_agent" in (routing_debug.get("selected_agents_from_features") or []),
        "routing_debug.selected_agents_from_features에 travel_event_agent가 없습니다.",
    )
    assert_true(
        "travel_planning_agent" in (routing_debug.get("auto_included_agents") or []),
        "routing_debug.auto_included_agents에 travel_planning_agent가 없습니다.",
    )


def test_jeju_day_trip_planning():
    payload = {
        "user_request": "",
        "destination": "제주",
        "location": "제주",
        "origin": "서울",
        "days": 1,
        "budget_level": "low",
        "requested_features": ["schedule", "weather", "transport"],
    }
    data = request_json("POST", "/run-workflow", payload)
    selected_agents = data.get("selected_agents", [])
    planning_result = find_agent_result(data, "travel_planning_agent")
    schedule_result = find_agent_result(data, "travel_schedule_agent")

    assert_planning_auto_included(data)
    assert_true("travel_schedule_agent" in selected_agents, "travel_schedule_agent가 선택되지 않았습니다.")
    assert_true("travel_weather_agent" in selected_agents, "travel_weather_agent가 선택되지 않았습니다.")
    assert_true("travel_transport_agent" in selected_agents, "travel_transport_agent가 선택되지 않았습니다.")
    assert_true(
        data.get("input_data_summary", {}).get("days") == 1,
        "input_data_summary.days가 1이 아닙니다.",
    )
    assert_true(planning_result is not None, "travel_planning_agent 결과가 없습니다.")

    planning_strategy = planning_result.get("duration_strategy") or {}
    assert_true(planning_strategy.get("days") == 1, "planning duration_strategy.days가 1이 아닙니다.")
    assert_true(planning_strategy.get("label") == "당일치기", "planning duration_strategy.label이 당일치기가 아닙니다.")
    assert_true(planning_strategy.get("lodging_required") is False, "planning lodging_required가 false가 아닙니다.")

    assert_true(schedule_result is not None, "travel_schedule_agent 결과가 없습니다.")
    schedule_strategy = schedule_result.get("duration_strategy") or {}
    assert_true(schedule_strategy, "travel_schedule_agent duration_strategy가 없습니다.")
    assert_true(schedule_strategy.get("label") == "당일치기", "schedule duration_strategy.label이 당일치기가 아닙니다.")


def test_busan_full_workflow():
    payload = {
        "user_request": "",
        "destination": "부산",
        "location": "부산",
        "origin": "서울",
        "days": 3,
        "budget_level": "medium",
        "requested_features": [
            "destination",
            "budget",
            "schedule",
            "weather",
            "tour",
            "transport",
        ],
    }
    data = request_json("POST", "/run-workflow", payload)
    selected_agents = data.get("selected_agents", [])
    agent_result_names = {
        result.get("agent") for result in data.get("agent_results", [])
    }
    assert_planning_auto_included(data)

    assert_true(len(selected_agents) >= 7, "selected_agents가 7개보다 작습니다.")
    assert_true(
        data.get("input_data_summary", {}).get("destination") == "부산",
        "input_data_summary.destination이 부산이 아닙니다.",
    )
    assert_true(
        "travel_weather_agent" in agent_result_names,
        "travel_weather_agent가 실행되지 않았습니다.",
    )
    assert_true(
        "travel_tour_agent" in agent_result_names,
        "travel_tour_agent가 실행되지 않았습니다.",
    )
    assert_true(
        "travel_transport_agent" in agent_result_names,
        "travel_transport_agent가 실행되지 않았습니다.",
    )
    assert_true(
        "travel_planning_agent" in agent_result_names,
        "travel_planning_agent가 실행되지 않았습니다.",
    )


def test_busan_lodging():
    payload = {
        "user_request": "",
        "destination": "부산",
        "location": "부산",
        "origin": "서울",
        "days": 3,
        "budget_level": "medium",
        "requested_features": ["lodging"],
    }
    data = request_json("POST", "/run-workflow", payload)
    selected_agents = data.get("selected_agents", [])
    
    assert_planning_auto_included(data)
    assert_true("travel_lodging_agent" in selected_agents, "travel_lodging_agent가 선택되지 않았습니다.")
    
    lodging_result = find_agent_result(data, "travel_lodging_agent")
    assert_true(lodging_result is not None, "travel_lodging_agent 결과가 없습니다.")
    assert_true(lodging_result.get("lodging_required") is True, "lodging_required가 True가 아닙니다.")
    assert_true(lodging_result.get("lodging_nights") == 2, "lodging_nights가 2가 아닙니다.")
    assert_true(len(lodging_result.get("lodging_items", [])) > 0, "숙소 추천 항목이 없습니다.")


def test_jeju_day_trip_lodging():
    payload = {
        "user_request": "",
        "destination": "제주",
        "location": "제주",
        "origin": "서울",
        "days": 1,
        "budget_level": "low",
        "requested_features": ["lodging"],
    }
    data = request_json("POST", "/run-workflow", payload)
    selected_agents = data.get("selected_agents", [])
    
    assert_planning_auto_included(data)
    assert_true("travel_lodging_agent" in selected_agents, "travel_lodging_agent가 선택되지 않았습니다.")
    
    lodging_result = find_agent_result(data, "travel_lodging_agent")
    assert_true(lodging_result is not None, "travel_lodging_agent 결과가 없습니다.")
    assert_true(lodging_result.get("lodging_required") is False, "lodging_required가 False가 아닙니다.")
    assert_true(lodging_result.get("lodging_nights") == 0, "lodging_nights가 0이 아닙니다.")
    assert_true(lodging_result.get("debug_info", {}).get("fallback_reason") == "day_trip_no_lodging_required", "당일치기 예외 사유가 올바르지 않습니다.")


def run_test(name, test_func):
    try:
        test_func()
    except SmokeTestError as exc:
        print(f"[FAIL] {name}")
        print(f"reason: {exc}")
        return False
    except Exception as exc:
        print(f"[FAIL] {name}")
        print(f"reason: unexpected error: {exc}")
        return False

    print(f"[PASS] {name}")
    return True


def main():
    tests = [
        ("health", test_health),
        ("agent library", test_agent_library),
        ("feature map", test_feature_map),
        ("jeju weather", test_jeju_weather),
        ("jeju transport", test_jeju_transport),
        ("seoul busan transport", test_seoul_busan_transport),
        ("busan destination", test_busan_destination),
        ("busan budget", test_busan_budget),
        ("busan integrated schedule", test_busan_integrated_schedule),
        ("jeju food", test_jeju_food),
        ("jeju event", test_jeju_event),
        ("jeju day trip planning", test_jeju_day_trip_planning),
        ("busan full workflow", test_busan_full_workflow),
        ("busan lodging", test_busan_lodging),
        ("jeju day trip lodging", test_jeju_day_trip_lodging),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        if run_test(name, test_func):
            passed += 1
        else:
            failed += 1

    print(f"Smoke test result: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
