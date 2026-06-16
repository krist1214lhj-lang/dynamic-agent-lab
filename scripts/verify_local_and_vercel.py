# Run from the project root:
# python scripts/verify_local_and_vercel.py
#
# Optional:
# python scripts/verify_local_and_vercel.py --vercel-url https://your-app.vercel.app
# $env:VERCEL_URL="https://your-app.vercel.app"; python scripts\verify_local_and_vercel.py

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCAL_URL = "http://127.0.0.1:8013"
DEFAULT_VERCEL_URL = "https://dynamic-agent-lab.vercel.app"
REQUEST_TIMEOUT_SECONDS = 45
VERCEL_ODSAY_API_KEY_LOADED = None

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

ALLOWED_TRANSPORT_DATA_SOURCES = {
    "odsay_api",
    "mock_fallback",
    "rule_based_fallback",
}

ALLOWED_DESTINATION_DATA_SOURCES = {
    "tour_api",
    "mock_fallback",
    "rule_based_fallback",
}

ALLOWED_BUDGET_DATA_SOURCES = {
    "rule_based_budget",
}

ALLOWED_SCHEDULE_DATA_SOURCES = {
    "integrated_rule_schedule",
    "rule_based_schedule",
    "mock_fallback",
}

ALLOWED_LODGING_DATA_SOURCES = {
    "tour_api",
    "mock_fallback",
    "rule_based_fallback",
}

API_ENV_NAMES = [
    "KMA_SERVICE_KEY",
    "TOUR_API_SERVICE_KEY",
    "ODSAY_API_KEY",
]

PLACEHOLDER_VALUES = {
    "your_kma_service_key_here",
    "your_tour_api_service_key_here",
    "your_odsay_api_key_here",
}

FALLBACK_CHECK_AGENTS = {
    "travel_destination_agent",
    "travel_weather_agent",
    "travel_tour_agent",
    "travel_food_agent",
    "travel_event_agent",
    "travel_transport_agent",
    "travel_lodging_agent",
}


class VerificationError(Exception):
    pass


@dataclass(frozen=True)
class Case:
    name: str
    method: str
    path: str
    payload: dict[str, Any] | None = None


CASES = [
    Case("health", "GET", "/health"),
    Case("feature map", "GET", "/feature-map"),
    Case("agent library", "GET", "/agent-library"),
    Case(
        "jeju weather",
        "POST",
        "/run-workflow",
        {
            "user_request": "",
            "destination": "제주",
            "location": "제주",
            "origin": "서울",
            "days": 3,
            "budget_level": "medium",
            "requested_features": ["weather"],
        },
    ),
    Case(
        "jeju transport",
        "POST",
        "/run-workflow",
        {
            "user_request": "",
            "destination": "제주",
            "location": "제주",
            "origin": "서울",
            "days": 3,
            "budget_level": "medium",
            "requested_features": ["transport"],
        },
    ),
    Case(
        "seoul busan transport",
        "POST",
        "/run-workflow",
        {
            "user_request": "",
            "destination": "부산",
            "location": "부산",
            "origin": "서울",
            "days": 2,
            "budget_level": "medium",
            "requested_features": ["transport"],
        },
    ),
    Case(
        "busan destination",
        "POST",
        "/run-workflow",
        {
            "user_request": "",
            "destination": "부산",
            "location": "부산",
            "origin": "서울",
            "days": 3,
            "budget_level": "medium",
            "requested_features": ["destination"],
        },
    ),
    Case(
        "busan budget",
        "POST",
        "/run-workflow",
        {
            "user_request": "",
            "destination": "부산",
            "location": "부산",
            "origin": "서울",
            "days": 3,
            "budget_level": "medium",
            "requested_features": ["budget"],
        },
    ),
    Case(
        "busan integrated schedule",
        "POST",
        "/run-workflow",
        {
            "user_request": "",
            "destination": "부산",
            "location": "부산",
            "origin": "서울",
            "days": 3,
            "budget_level": "medium",
            "requested_features": ["schedule", "transport", "budget", "food", "event", "tour"],
        },
    ),
    Case(
        "jeju food",
        "POST",
        "/run-workflow",
        {
            "user_request": "",
            "destination": "제주",
            "location": "제주",
            "origin": "서울",
            "days": 3,
            "budget_level": "low",
            "requested_features": ["food"],
        },
    ),
    Case(
        "jeju event",
        "POST",
        "/run-workflow",
        {
            "user_request": "",
            "destination": "제주",
            "location": "제주",
            "origin": "서울",
            "days": 3,
            "budget_level": "low",
            "requested_features": ["event"],
        },
    ),
    Case(
        "jeju day trip planning",
        "POST",
        "/run-workflow",
        {
            "user_request": "",
            "destination": "제주",
            "location": "제주",
            "origin": "서울",
            "days": 1,
            "budget_level": "low",
            "requested_features": ["schedule", "weather", "transport"],
        },
    ),
    Case(
        "busan full workflow",
        "POST",
        "/run-workflow",
        {
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
        },
    ),
    Case(
        "busan lodging",
        "POST",
        "/run-workflow",
        {
            "user_request": "",
            "destination": "부산",
            "location": "부산",
            "origin": "서울",
            "days": 3,
            "budget_level": "medium",
            "requested_features": ["lodging"],
        },
    ),
    Case(
        "jeju day trip lodging",
        "POST",
        "/run-workflow",
        {
            "user_request": "",
            "destination": "제주",
            "location": "제주",
            "origin": "서울",
            "days": 1,
            "budget_level": "low",
            "requested_features": ["lodging"],
        },
    ),
]


def normalize_base_url(url: str) -> str:
    normalized = url.strip().rstrip("/")
    if not normalized:
        raise VerificationError("URL is empty.")
    if "://" not in normalized:
        normalized = f"https://{normalized}"
    return normalized


def request_json(base_url: str, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"{base_url}{path}"
    body = None
    headers = {"Accept": "application/json"}

    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise VerificationError(f"{method} {url} returned HTTP {exc.code}: {raw}") from exc
    except urllib.error.URLError as exc:
        raise VerificationError(f"{method} {url} failed: {exc.reason}") from exc
    except TimeoutError as exc:
        raise VerificationError(f"{method} {url} timed out.") from exc
    except OSError as exc:
        raise VerificationError(f"{method} {url} failed: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise VerificationError(f"{method} {url} did not return JSON.") from exc

    if not isinstance(data, dict):
        raise VerificationError(f"{method} {url} returned a non-object JSON response.")
    return data


def url_is_healthy(base_url: str) -> bool:
    try:
        data = request_json(base_url, "GET", "/health")
    except VerificationError:
        return False
    return data.get("status") == "ok"


def parse_local_host_port(local_url: str) -> tuple[str, int]:
    parsed = urllib.parse.urlparse(local_url)
    if parsed.scheme not in {"http", "https"}:
        raise VerificationError(f"Unsupported local URL scheme: {local_url}")
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise VerificationError(
            "Automatic local server startup only supports localhost, 127.0.0.1, or ::1."
        )
    if not parsed.port:
        raise VerificationError(f"Local URL must include a port: {local_url}")
    return parsed.hostname, parsed.port


def start_local_server(local_url: str) -> subprocess.Popen[str] | None:
    if url_is_healthy(local_url):
        print(f"[INFO] local server already healthy: {local_url}")
        return None

    host, port = parse_local_host_port(local_url)
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]

    print(f"[INFO] starting local server: {' '.join(command)}")
    process = subprocess.Popen(
        command,
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            output = process.stdout.read() if process.stdout else ""
            raise VerificationError(f"Local server exited early with code {process.returncode}.\n{output}")
        if url_is_healthy(local_url):
            print(f"[INFO] local server healthy: {local_url}")
            return process
        time.sleep(0.5)

    process.terminate()
    output = process.stdout.read() if process.stdout else ""
    raise VerificationError(f"Local server did not become healthy within 30 seconds.\n{output}")


def stop_local_server(process: subprocess.Popen[str] | None) -> None:
    if process is None:
        return

    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def assert_true(condition: bool, reason: str) -> None:
    if not condition:
        raise VerificationError(reason)


def find_agent_result(data: dict[str, Any], agent_name: str) -> dict[str, Any] | None:
    for result in data.get("agent_results", []):
        if result.get("agent") == agent_name:
            return result
    return None


def local_env_value(name: str) -> str:
    value = os.environ.get(name)
    if value:
        return value

    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return ""

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, raw_value = stripped.split("=", 1)
        if key.strip() == name:
            return raw_value.strip().strip('"').strip("'")
    return ""


def assert_known_api_key_not_leaked(label: str, data: dict[str, Any], env_name: str) -> None:
    key_value = local_env_value(env_name)
    if not key_value:
        return
    serialized = json.dumps(data, ensure_ascii=False)
    assert_true(key_value not in serialized, f"{label} leaked raw {env_name}.")


def assert_no_api_secret_or_placeholder_leaked(label: str, data: dict[str, Any]) -> None:
    serialized = json.dumps(data, ensure_ascii=False)
    for env_name in API_ENV_NAMES:
        assert_known_api_key_not_leaked(label, data, env_name)
    for placeholder in PLACEHOLDER_VALUES:
        assert_true(placeholder not in serialized, f"{label} leaked placeholder value {placeholder}.")


def fallback_reason_for(result: dict[str, Any]) -> Any:
    debug_info = result.get("debug_info") if isinstance(result.get("debug_info"), dict) else {}
    api_debug = result.get("api_debug") if isinstance(result.get("api_debug"), dict) else {}
    for source in [debug_info, api_debug, result]:
        for key in ["fallback_reason", "debug_message", "last_error"]:
            value = source.get(key)
            if value:
                return value

    for field in ["weather_findings", "tour_findings", "food_findings", "event_findings"]:
        values = result.get(field)
        if isinstance(values, list):
            for value in values:
                if "fallback_reason=" in str(value):
                    return value
    return None


def assert_fallback_reasons(label: str, data: dict[str, Any]) -> None:
    for result in data.get("agent_results", []):
        agent_name = result.get("agent")
        data_source = result.get("data_source")
        if agent_name not in FALLBACK_CHECK_AGENTS:
            continue
        if data_source not in {"mock_fallback", "rule_based_fallback"}:
            continue
        assert_true(
            bool(fallback_reason_for(result)),
            f"{label} {agent_name} uses {data_source} without fallback reason.",
        )


def text_in_route(route: dict[str, Any], keyword: str) -> bool:
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


def first_intercity_route(routes: list[dict[str, Any]]) -> dict[str, Any]:
    for route in routes:
        if route.get("type") == "intercity":
            return route
    return routes[0] if routes else {}


def assert_seoul_busan_transport_contract(label: str, data: dict[str, Any]) -> None:
    selected_agents = data.get("selected_agents") or []
    loaded_agent_names = {agent.get("name") for agent in data.get("loaded_agents", [])}
    transport_result = find_agent_result(data, "travel_transport_agent")

    assert_true(
        selected_agents and selected_agents[0] == "travel_planning_agent",
        f"{label} did not run travel_planning_agent first.",
    )
    assert_true(
        "travel_transport_agent" in selected_agents,
        f"{label} did not select travel_transport_agent.",
    )
    assert_true(
        "travel_transport_agent" in loaded_agent_names,
        f"{label} did not load travel_transport_agent.",
    )
    assert_true(transport_result is not None, f"{label} has no transport result.")

    data_source = transport_result.get("data_source")
    assert_true(
        data_source in ALLOWED_TRANSPORT_DATA_SOURCES,
        f"{label} transport data_source is not allowed: {data_source}",
    )

    debug_info = transport_result.get("debug_info") or {}
    if data_source != "odsay_api":
        assert_true(
            bool(debug_info.get("fallback_reason")),
            f"{label} fallback transport has no debug_info.fallback_reason.",
        )
    assert_true(
        debug_info.get("service_key_leaked") is False,
        f"{label} debug_info.service_key_leaked is not false.",
    )
    assert_known_api_key_not_leaked(label, data, "ODSAY_API_KEY")


def assert_busan_destination_contract(label: str, data: dict[str, Any]) -> None:
    selected_agents = data.get("selected_agents") or []
    loaded_agent_names = {agent.get("name") for agent in data.get("loaded_agents", [])}
    destination_result = find_agent_result(data, "travel_destination_agent")

    assert_true(
        selected_agents and selected_agents[0] == "travel_planning_agent",
        f"{label} did not run travel_planning_agent first.",
    )
    assert_true(
        "travel_destination_agent" in selected_agents,
        f"{label} did not select travel_destination_agent.",
    )
    assert_true(
        "travel_destination_agent" in loaded_agent_names,
        f"{label} did not load travel_destination_agent.",
    )
    assert_true(destination_result is not None, f"{label} has no destination result.")

    data_source = destination_result.get("data_source")
    assert_true(
        data_source in ALLOWED_DESTINATION_DATA_SOURCES,
        f"{label} destination data_source is not allowed: {data_source}",
    )
    recommendations = (
        destination_result.get("recommendations")
        or destination_result.get("destinations")
        or []
    )
    assert_true(bool(recommendations), f"{label} has no destination recommendations.")

    debug_info = destination_result.get("debug_info") or {}
    if data_source != "tour_api":
        assert_true(
            bool(debug_info.get("fallback_reason")),
            f"{label} fallback destination has no debug_info.fallback_reason.",
        )
    assert_true(
        debug_info.get("service_key_leaked") is False,
        f"{label} debug_info.service_key_leaked is not false.",
    )
    assert_known_api_key_not_leaked(label, data, "TOUR_API_SERVICE_KEY")


def assert_busan_budget_contract(label: str, data: dict[str, Any]) -> None:
    selected_agents = data.get("selected_agents") or []
    loaded_agent_names = {agent.get("name") for agent in data.get("loaded_agents", [])}
    budget_result = find_agent_result(data, "travel_budget_agent")

    assert_true(
        selected_agents and selected_agents[0] == "travel_planning_agent",
        f"{label} did not run travel_planning_agent first.",
    )
    assert_true(
        "travel_budget_agent" in selected_agents,
        f"{label} did not select travel_budget_agent.",
    )
    assert_true(
        "travel_budget_agent" in loaded_agent_names,
        f"{label} did not load travel_budget_agent.",
    )
    assert_true(budget_result is not None, f"{label} has no budget result.")

    data_source = budget_result.get("data_source")
    assert_true(
        data_source in ALLOWED_BUDGET_DATA_SOURCES,
        f"{label} budget data_source is not allowed: {data_source}",
    )
    assert_true(
        budget_result.get("estimated_total_krw", 0) > 0,
        f"{label} estimated_total_krw is not positive.",
    )
    breakdown = budget_result.get("budget_breakdown") or {}
    for key in ["transport", "lodging", "food", "tour_event", "buffer"]:
        assert_true(key in breakdown, f"{label} budget_breakdown has no {key}.")
    assert_true(breakdown.get("transport", 0) > 0, f"{label} transport budget is not positive.")
    assert_true(breakdown.get("food", 0) > 0, f"{label} food budget is not positive.")
    assert_true(
        budget_result.get("duration_label") == "2박 3일",
        f"{label} duration_label is not 2박 3일.",
    )
    assert_true(
        budget_result.get("lodging_required") is True,
        f"{label} lodging_required is not true.",
    )


def assert_busan_integrated_schedule_contract(label: str, data: dict[str, Any]) -> None:
    selected_agents = data.get("selected_agents") or []
    loaded_agent_names = {agent.get("name") for agent in data.get("loaded_agents", [])}
    schedule_result = find_agent_result(data, "travel_schedule_agent")

    assert_true(
        selected_agents and selected_agents[0] == "travel_planning_agent",
        f"{label} did not run travel_planning_agent first.",
    )
    for agent_name in [
        "travel_schedule_agent",
        "travel_transport_agent",
        "travel_budget_agent",
        "travel_food_agent",
        "travel_event_agent",
        "travel_tour_agent",
    ]:
        assert_true(agent_name in selected_agents, f"{label} did not select {agent_name}.")
        assert_true(agent_name in loaded_agent_names, f"{label} did not load {agent_name}.")

    assert_true(schedule_result is not None, f"{label} has no schedule result.")
    data_source = schedule_result.get("data_source")
    assert_true(
        data_source in ALLOWED_SCHEDULE_DATA_SOURCES,
        f"{label} schedule data_source is not allowed: {data_source}",
    )

    daily_itinerary = schedule_result.get("daily_itinerary")
    assert_true(isinstance(daily_itinerary, list), f"{label} daily_itinerary is not a list.")
    assert_true(len(daily_itinerary) >= 1, f"{label} daily_itinerary is empty.")
    assert_true(
        len(daily_itinerary) == 3,
        f"{label} daily_itinerary length is not 3: {len(daily_itinerary)}",
    )
    for day in daily_itinerary:
        assert_true(isinstance(day.get("time_blocks"), list), f"{label} day has no time_blocks list.")

    duration_strategy = schedule_result.get("duration_strategy") or {}
    assert_true(
        duration_strategy.get("label") == "2박 3일",
        f"{label} duration_strategy.label is not 2박 3일.",
    )
    assert_true(bool(schedule_result.get("schedule_summary")), f"{label} has no schedule_summary.")


def assert_common_contract(case: Case, label: str, data: dict[str, Any]) -> None:
    if case.path == "/health":
        assert_true(data.get("status") == "ok", f"{label} health status is not ok.")
        assert_true(
            data.get("available_agents", 0) >= len(EXPECTED_AGENTS),
            f"{label} available_agents is smaller than {len(EXPECTED_AGENTS)}.",
        )
        env_loaded = data.get("env_loaded") or {}
        for env_name in API_ENV_NAMES:
            assert_true(env_name in env_loaded, f"{label} health env_loaded has no {env_name}.")
            assert_true(
                isinstance(env_loaded.get(env_name), bool),
                f"{label} health env_loaded.{env_name} is not boolean.",
            )
        return

    if case.path == "/feature-map":
        features = data.get("features") or {}
        for feature, expected_agent in EXPECTED_FEATURE_MAP.items():
            assert_true(
                features.get(feature) == expected_agent,
                f"{label} feature {feature} is not mapped to {expected_agent}.",
            )
        assert_true(
            data.get("feature_count", 0) >= len(EXPECTED_FEATURE_MAP),
            f"{label} feature_count is smaller than {len(EXPECTED_FEATURE_MAP)}.",
        )
        return

    if case.path == "/agent-library":
        agent_names = {agent.get("name") for agent in data.get("agents", [])}
        missing = sorted(EXPECTED_AGENTS - agent_names)
        assert_true(not missing, f"{label} is missing agents: {', '.join(missing)}")
        assert_true(
            data.get("available_count", 0) >= len(EXPECTED_AGENTS),
            f"{label} available_count is smaller than {len(EXPECTED_AGENTS)}.",
        )
        return

    if case.path == "/run-workflow":
        assert_workflow_contract(case, label, data)


def assert_workflow_contract(case: Case, label: str, data: dict[str, Any]) -> None:
    payload = case.payload or {}
    requested_features = payload.get("requested_features") or []
    expected_agents = [
        EXPECTED_FEATURE_MAP[feature]
        for feature in requested_features
        if feature in EXPECTED_FEATURE_MAP
    ]
    selected_agents = data.get("selected_agents") or []
    loaded_agent_names = {agent.get("name") for agent in data.get("loaded_agents", [])}

    assert_true(
        selected_agents and selected_agents[0] == "travel_planning_agent",
        f"{label} did not run travel_planning_agent first.",
    )
    assert_true(
        "travel_planning_agent" in loaded_agent_names,
        f"{label} did not load travel_planning_agent.",
    )

    for expected_agent in expected_agents:
        assert_true(expected_agent in selected_agents, f"{label} did not select {expected_agent}.")
        assert_true(expected_agent in loaded_agent_names, f"{label} did not load {expected_agent}.")

    summary = data.get("input_data_summary") or {}
    for key in ["destination", "location", "origin", "days", "budget_level"]:
        assert_true(summary.get(key) == payload.get(key), f"{label} summary.{key} differs from payload.")

    for result in data.get("agent_results", []):
        assert_true("error" not in result, f"{label} agent {result.get('agent')} returned an error.")

    assert_true(data.get("validation_report") is not None, f"{label} has no validation_report.")
    assert_fallback_reasons(label, data)

    if case.name == "jeju weather":
        weather_result = find_agent_result(data, "travel_weather_agent")
        assert_true(weather_result is not None, f"{label} has no weather result.")
        assert_true(weather_result.get("location") == "제주", f"{label} weather location is not 제주.")
        forecast = weather_result.get("forecast") or {}
        weather_summary = weather_result.get("weather_summary") or {}
        assert_true(
            bool(
                forecast.get("temperature")
                or forecast.get("condition")
                or weather_summary.get("temperature")
                or weather_summary.get("condition")
            ),
            f"{label} weather result has no temperature or condition.",
        )

    if case.name == "jeju transport":
        transport_result = find_agent_result(data, "travel_transport_agent")
        assert_true(transport_result is not None, f"{label} has no transport result.")
        routes = transport_result.get("routes") or []
        assert_true(any(text_in_route(route, "항공편") for route in routes), f"{label} has no flight route.")
        assert_true(any(text_in_route(route, "선박") for route in routes), f"{label} has no ship route.")
        assert_true(
            not text_in_route(first_intercity_route(routes), "KTX"),
            f"{label} first intercity route recommends KTX for 제주.",
        )

    if case.name == "seoul busan transport":
        assert_seoul_busan_transport_contract(label, data)

    if case.name == "busan destination":
        assert_busan_destination_contract(label, data)

    if case.name == "busan budget":
        assert_busan_budget_contract(label, data)

    if case.name == "busan integrated schedule":
        assert_busan_integrated_schedule_contract(label, data)

    if case.name == "jeju food":
        food_result = find_agent_result(data, "travel_food_agent")
        assert_true(food_result is not None, f"{label} has no food result.")
        food_items = food_result.get("food_items") or []
        assert_true(len(food_items) >= 3, f"{label} food_items has fewer than 3 items.")

    if case.name == "jeju event":
        event_result = find_agent_result(data, "travel_event_agent")
        assert_true(event_result is not None, f"{label} has no event result.")
        event_items = event_result.get("event_items") or []
        assert_true(len(event_items) >= 3, f"{label} event_items has fewer than 3 items.")

    if case.name == "jeju day trip planning":
        planning_result = find_agent_result(data, "travel_planning_agent")
        schedule_result = find_agent_result(data, "travel_schedule_agent")
        assert_true(planning_result is not None, f"{label} has no planning result.")
        planning_strategy = planning_result.get("duration_strategy") or {}
        assert_true(planning_strategy.get("days") == 1, f"{label} planning days is not 1.")
        assert_true(planning_strategy.get("label") == "당일치기", f"{label} planning label is not 당일치기.")
        assert_true(planning_strategy.get("lodging_required") is False, f"{label} planning lodging_required is not false.")
        assert_true(schedule_result is not None, f"{label} has no schedule result.")
        schedule_strategy = schedule_result.get("duration_strategy") or {}
        assert_true(schedule_strategy.get("label") == "당일치기", f"{label} schedule label is not 당일치기.")

    if case.name == "busan full workflow":
        assert_true(len(selected_agents) >= 7, f"{label} selected fewer than 7 agents.")
        result_names = {result.get("agent") for result in data.get("agent_results", [])}
        for agent_name in [
            "travel_planning_agent",
            "travel_weather_agent",
            "travel_tour_agent",
            "travel_transport_agent",
        ]:
            assert_true(agent_name in result_names, f"{label} did not run {agent_name}.")

    if case.name == "busan lodging":
        lodging_result = find_agent_result(data, "travel_lodging_agent")
        assert_true(lodging_result is not None, f"{label} has no lodging result.")
        assert_true(lodging_result.get("lodging_required") is True, f"{label} lodging_required is not true.")
        assert_true(lodging_result.get("lodging_nights") == 2, f"{label} lodging_nights is not 2.")
        assert_true(
            lodging_result.get("data_source") in ALLOWED_LODGING_DATA_SOURCES,
            f"{label} lodging data_source is not allowed: {lodging_result.get('data_source')}",
        )

    if case.name == "jeju day trip lodging":
        lodging_result = find_agent_result(data, "travel_lodging_agent")
        assert_true(lodging_result is not None, f"{label} has no lodging result.")
        assert_true(lodging_result.get("lodging_required") is False, f"{label} lodging_required is not false.")
        assert_true(lodging_result.get("lodging_nights") == 0, f"{label} lodging_nights is not 0.")
        assert_true(
            lodging_result.get("debug_info", {}).get("fallback_reason") == "day_trip_no_lodging_required",
            f"{label} day trip fallback reason is incorrect.",
        )


def transport_source_summary(data: dict[str, Any]) -> tuple[Any, Any]:
    transport_result = find_agent_result(data, "travel_transport_agent") or {}
    debug_info = transport_result.get("debug_info") or {}
    return transport_result.get("data_source"), fallback_reason_for(transport_result)


def budget_signature(data: dict[str, Any]) -> tuple[Any, Any]:
    budget_result = find_agent_result(data, "travel_budget_agent") or {}
    return (
        budget_result.get("estimated_total_krw"),
        budget_result.get("budget_breakdown") or {},
    )


def agent_result_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        result.get("agent"): result
        for result in data.get("agent_results", [])
        if result.get("agent")
    }


def report_health_env(local_data: dict[str, Any], vercel_data: dict[str, Any]) -> None:
    global VERCEL_ODSAY_API_KEY_LOADED
    local_env = local_data.get("env_loaded") or {}
    vercel_env = vercel_data.get("env_loaded") or {}
    local_odsay = local_env.get("ODSAY_API_KEY")
    vercel_odsay = vercel_env.get("ODSAY_API_KEY")
    VERCEL_ODSAY_API_KEY_LOADED = vercel_odsay
    print(
        "[INFO] health env_loaded ODSAY_API_KEY: "
        f"local={local_odsay}; vercel={vercel_odsay}"
    )
    if vercel_odsay is False:
        print("[INFO] Vercel ODSAY_API_KEY is not loaded; transport will use fallback.")


def report_data_source_differences(case: Case, local_data: dict[str, Any], vercel_data: dict[str, Any]) -> None:
    if case.path != "/run-workflow":
        return

    local_results = agent_result_map(local_data)
    vercel_results = agent_result_map(vercel_data)
    for agent_name in sorted(set(local_results) & set(vercel_results)):
        if case.name == "seoul busan transport" and agent_name == "travel_transport_agent":
            continue
        local_source = local_results[agent_name].get("data_source")
        vercel_source = vercel_results[agent_name].get("data_source")
        if not local_source and not vercel_source:
            continue
        if local_source == vercel_source:
            continue

        local_reason = fallback_reason_for(local_results[agent_name]) or "-"
        vercel_reason = fallback_reason_for(vercel_results[agent_name]) or "-"
        print(
            f"[INFO] {case.name} {agent_name} data_source differs: "
            f"local={local_source} fallback_reason={local_reason}; "
            f"vercel={vercel_source} fallback_reason={vercel_reason}"
        )

    vercel_transport = vercel_results.get("travel_transport_agent")
    if vercel_transport and vercel_transport.get("data_source") != "odsay_api":
        if VERCEL_ODSAY_API_KEY_LOADED is True:
            print(
                "[INFO] Vercel ODSAY_API_KEY is loaded, but ODsay call fell back. "
                "Check Server IP restriction or API response."
            )


def run_case(case: Case, local_url: str, vercel_url: str) -> bool:
    try:
        local_data = request_json(local_url, case.method, case.path, case.payload)
        vercel_data = request_json(vercel_url, case.method, case.path, case.payload)

        assert_common_contract(case, "local", local_data)
        assert_common_contract(case, "vercel", vercel_data)
        assert_no_api_secret_or_placeholder_leaked("local", local_data)
        assert_no_api_secret_or_placeholder_leaked("vercel", vercel_data)

        if case.path == "/health":
            report_health_env(local_data, vercel_data)

        report_data_source_differences(case, local_data, vercel_data)

        if case.name == "seoul busan transport":
            local_source, local_reason = transport_source_summary(local_data)
            vercel_source, vercel_reason = transport_source_summary(vercel_data)
            if local_source != vercel_source:
                assert_true(
                    vercel_source == "odsay_api" or bool(vercel_reason),
                    "vercel seoul busan transport fallback_reason is missing.",
                )
                print(
                    "[INFO] seoul busan transport data_source differs: "
                    f"local={local_source} fallback_reason={local_reason or '-'}; "
                    f"vercel={vercel_source} fallback_reason={vercel_reason or '-'}"
                )
            else:
                print(
                    "[INFO] seoul busan transport data_source: "
                    f"local={local_source}; vercel={vercel_source}; "
                    f"fallback_reason={vercel_reason or local_reason or '-'}"
                )
            print(f"[PASS] {case.name}")
            return True

        if case.name == "busan budget":
            local_budget = budget_signature(local_data)
            vercel_budget = budget_signature(vercel_data)
            assert_true(
                local_budget == vercel_budget,
                f"busan budget differs: local={local_budget}; vercel={vercel_budget}",
            )
            print(
                "[INFO] busan budget rule_based_budget total: "
                f"local={local_budget[0]}; vercel={vercel_budget[0]}"
            )
            print(f"[PASS] {case.name}")
            return True

        if case.name == "busan integrated schedule":
            local_schedule = find_agent_result(local_data, "travel_schedule_agent") or {}
            vercel_schedule = find_agent_result(vercel_data, "travel_schedule_agent") or {}
            local_days = len(local_schedule.get("daily_itinerary") or [])
            vercel_days = len(vercel_schedule.get("daily_itinerary") or [])
            print(
                "[INFO] busan integrated schedule days: "
                f"local={local_days} source={local_schedule.get('data_source')}; "
                f"vercel={vercel_days} source={vercel_schedule.get('data_source')}"
            )
            print(f"[PASS] {case.name}")
            return True

    except VerificationError as exc:
        print(f"[FAIL] {case.name}")
        print(f"reason: {exc}")
        return False

    print(f"[PASS] {case.name}")
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify that local dynamic-agent-lab and the Vercel deployment behave the same."
    )
    parser.add_argument(
        "--local-url",
        default=os.environ.get("LOCAL_URL", DEFAULT_LOCAL_URL),
        help=f"Local app URL. Defaults to {DEFAULT_LOCAL_URL}.",
    )
    parser.add_argument(
        "--vercel-url",
        default=os.environ.get("VERCEL_URL", DEFAULT_VERCEL_URL),
        help=f"Vercel deployment URL. Defaults to {DEFAULT_VERCEL_URL}.",
    )
    parser.add_argument(
        "--no-start-local",
        action="store_true",
        help="Do not start uvicorn automatically; require the local URL to already be healthy.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    local_url = normalize_base_url(args.local_url)
    vercel_url = normalize_base_url(args.vercel_url)
    local_process = None

    print(f"[INFO] local URL: {local_url}")
    print(f"[INFO] Vercel URL: {vercel_url}")

    try:
        if args.no_start_local:
            if not url_is_healthy(local_url):
                raise VerificationError(f"Local URL is not healthy: {local_url}")
        else:
            local_process = start_local_server(local_url)

        passed = 0
        failed = 0
        for case in CASES:
            if run_case(case, local_url, vercel_url):
                passed += 1
            else:
                failed += 1

        print(f"Local/Vercel verification result: {passed} passed, {failed} failed")
        return 0 if failed == 0 else 1
    except VerificationError as exc:
        print(f"[FAIL] verification setup")
        print(f"reason: {exc}")
        return 1
    finally:
        stop_local_server(local_process)


if __name__ == "__main__":
    sys.exit(main())
