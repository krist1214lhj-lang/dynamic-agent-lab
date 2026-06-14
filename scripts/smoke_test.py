# Run from the project root:
# python scripts/smoke_test.py

import json
import os
import sys
import urllib.error
import urllib.request


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
        ("jeju food", test_jeju_food),
        ("jeju event", test_jeju_event),
        ("jeju day trip planning", test_jeju_day_trip_planning),
        ("busan full workflow", test_busan_full_workflow),
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
