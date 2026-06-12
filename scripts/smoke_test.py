# Run from the project root:
# python scripts/smoke_test.py

import json
import os
import sys
import urllib.error
import urllib.request


BASE_URL = os.environ.get("BASE_URL", "http://localhost:8012")

EXPECTED_AGENTS = {
    "travel_destination_agent",
    "travel_budget_agent",
    "travel_schedule_agent",
    "travel_weather_agent",
    "travel_tour_agent",
    "travel_transport_agent",
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


def test_agent_library():
    data = request_json("GET", "/agent-library")
    agent_names = {agent.get("name") for agent in data.get("agents", [])}

    assert_true(data.get("total_agents", 0) >= 6, "total_agents가 6보다 작습니다.")
    assert_true(
        data.get("available_count", 0) >= 6,
        "available_count가 6보다 작습니다.",
    )
    missing = sorted(EXPECTED_AGENTS - agent_names)
    assert_true(not missing, f"누락된 에이전트: {', '.join(missing)}")


def test_health():
    data = request_json("GET", "/health")

    assert_true(data.get("status") == "ok", "health status가 ok가 아닙니다.")
    assert_true(
        data.get("available_agents", 0) >= 6,
        "available_agents가 6보다 작습니다.",
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

    assert_true(len(selected_agents) >= 6, "selected_agents가 6개보다 작습니다.")
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
        ("jeju weather", test_jeju_weather),
        ("jeju transport", test_jeju_transport),
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
