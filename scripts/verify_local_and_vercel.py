# Run from the project root:
# python scripts/verify_local_and_vercel.py
#
# Optional:
# python scripts/verify_local_and_vercel.py --vercel-url https://your-app.vercel.app
# $env:VERCEL_URL="https://your-app.vercel.app"; python scripts\verify_local_and_vercel.py

import argparse
import copy
import difflib
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

EXPECTED_AGENTS = {
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


def assert_common_contract(case: Case, label: str, data: dict[str, Any]) -> None:
    if case.path == "/health":
        assert_true(data.get("status") == "ok", f"{label} health status is not ok.")
        assert_true(
            data.get("available_agents", 0) >= len(EXPECTED_AGENTS),
            f"{label} available_agents is smaller than {len(EXPECTED_AGENTS)}.",
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

    for expected_agent in expected_agents:
        assert_true(expected_agent in selected_agents, f"{label} did not select {expected_agent}.")
        assert_true(expected_agent in loaded_agent_names, f"{label} did not load {expected_agent}.")

    summary = data.get("input_data_summary") or {}
    for key in ["destination", "location", "origin", "days", "budget_level"]:
        assert_true(summary.get(key) == payload.get(key), f"{label} summary.{key} differs from payload.")

    for result in data.get("agent_results", []):
        assert_true("error" not in result, f"{label} agent {result.get('agent')} returned an error.")

    assert_true(data.get("validation_report") is not None, f"{label} has no validation_report.")

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

    if case.name == "busan full workflow":
        assert_true(len(selected_agents) >= 6, f"{label} selected fewer than 6 agents.")
        result_names = {result.get("agent") for result in data.get("agent_results", [])}
        for agent_name in [
            "travel_weather_agent",
            "travel_tour_agent",
            "travel_transport_agent",
        ]:
            assert_true(agent_name in result_names, f"{label} did not run {agent_name}.")


def stable_agent_library(data: dict[str, Any]) -> dict[str, Any]:
    agents = []
    for agent in data.get("agents", []):
        normalized = {
            key: value
            for key, value in agent.items()
            if key not in {"path", "source", "error"}
        }
        agents.append(normalized)

    return {
        "total_agents": data.get("total_agents"),
        "available_count": data.get("available_count"),
        "agents": sorted(agents, key=lambda item: item.get("name", "")),
    }


def scrub_unstable_values(value: Any) -> Any:
    if isinstance(value, dict):
        scrubbed = {}
        for key, child in value.items():
            if key in {
                "agent_library_path",
                "library_path",
                "path",
                "env_loaded",
                "debug_info",
                "debug_message",
                "api_debug",
                "request_url_without_service_key",
                "key_loaded",
                "key_length",
                "key_preview",
                "base_date",
                "base_time",
                "condition",
                "rain_probability",
                "temperature",
                "weather_findings",
            }:
                continue
            scrubbed[key] = scrub_unstable_values(child)
        return scrubbed
    if isinstance(value, list):
        return [scrub_unstable_values(child) for child in value]
    return value


def stable_response(case: Case, data: dict[str, Any]) -> dict[str, Any]:
    stable = copy.deepcopy(data)
    if case.path == "/agent-library":
        return stable_agent_library(stable)
    return scrub_unstable_values(stable)


def stable_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)


def diff_responses(case: Case, local_data: dict[str, Any], vercel_data: dict[str, Any]) -> list[str]:
    local_stable = stable_json(stable_response(case, local_data)).splitlines()
    vercel_stable = stable_json(stable_response(case, vercel_data)).splitlines()
    return list(
        difflib.unified_diff(
            local_stable,
            vercel_stable,
            fromfile=f"local:{case.name}",
            tofile=f"vercel:{case.name}",
            lineterm="",
        )
    )


def run_case(case: Case, local_url: str, vercel_url: str) -> bool:
    try:
        local_data = request_json(local_url, case.method, case.path, case.payload)
        vercel_data = request_json(vercel_url, case.method, case.path, case.payload)

        assert_common_contract(case, "local", local_data)
        assert_common_contract(case, "vercel", vercel_data)

        diff = diff_responses(case, local_data, vercel_data)
        if diff:
            print(f"[FAIL] {case.name}")
            print("reason: local and Vercel normalized responses differ")
            preview = diff[:160]
            print("\n".join(preview))
            if len(diff) > len(preview):
                print(f"... diff truncated ({len(diff) - len(preview)} more lines)")
            return False

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
