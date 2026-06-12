import importlib.util
import json
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from validators.travel_validator import validate_and_correct


app = FastAPI(title="dynamic-agent-lab")
app.mount("/static", StaticFiles(directory="static"), name="static")


class WorkflowRequest(BaseModel):
    user_request: str
    destination: str | None = None
    location: str | None = None
    origin: str | None = None
    days: int | None = None
    budget_level: str | None = None
    requested_features: list[str] = Field(default_factory=list)


class WorkflowResponse(BaseModel):
    user_request: str
    input_data: dict[str, Any]
    input_data_summary: dict[str, Any]
    routing_debug: dict[str, Any]
    selected_agents: list[str]
    loaded_agents: list[dict[str, Any]]
    agent_results: list[dict[str, Any]]
    validation_report: dict[str, Any]
    final_summary: str


SUPPORTED_DESTINATIONS = [
    "서울",
    "부산",
    "제주",
    "강릉",
    "전주",
    "대구",
    "대전",
    "광주",
    "인천",
    "여수",
    "경주",
    "속초",
    "춘천",
]


def external_agent_dir(path: str) -> Path:
    agent_path = Path(path)
    if agent_path.exists() or not path.startswith("/mnt/d/"):
        return agent_path
    return Path("D:/") / path.removeprefix("/mnt/d/")


INTERNAL_AGENT_LIBRARY = BASE_DIR / "agents"
EXTERNAL_AGENT_LIBRARY = external_agent_dir("/mnt/d/AI_AGENT_LIBRARY")


AGENT_NAMES = [
    "travel_destination_agent",
    "travel_budget_agent",
    "travel_schedule_agent",
    "travel_weather_agent",
    "travel_tour_agent",
    "travel_transport_agent",
]

ROUTING_RULES: dict[str, list[str]] = {
    "travel_destination_agent": ["여행지", "추천", "도시", "어디"],
    "travel_budget_agent": ["예산", "비용", "돈", "저렴"],
    "travel_schedule_agent": ["일정", "코스", "몇박", "2박", "3일", "계획"],
    "travel_weather_agent": ["날씨", "기온", "비", "우산", "강수", "흐림", "맑음"],
    "travel_tour_agent": ["관광지", "명소", "볼거리", "행사", "축제", "숙박", "호텔", "사진", "투어"],
    "travel_food_agent": ["맛집", "음식", "식당", "먹거리", "로컬푸드", "향토음식", "점심", "저녁"],
    "travel_transport_agent": ["교통", "이동", "지하철", "버스", "택시", "기차", "KTX", "공항", "노선", "동선"],
}

FEATURE_AGENT_MAP: dict[str, str] = {
    "destination": "travel_destination_agent",
    "budget": "travel_budget_agent",
    "schedule": "travel_schedule_agent",
    "weather": "travel_weather_agent",
    "tour": "travel_tour_agent",
    "food": "travel_food_agent",
    "transport": "travel_transport_agent",
}


def select_agents(user_request: str) -> list[str]:
    selected_agents = [
        agent_name
        for agent_name, keywords in ROUTING_RULES.items()
        if any(keyword in user_request for keyword in keywords)
    ]

    if not selected_agents:
        selected_agents.append("travel_destination_agent")

    return selected_agents


def select_agents_from_features(requested_features: list[str]) -> list[str]:
    selected_agents = []
    for feature in requested_features:
        normalized_feature = str(feature).strip().lower()
        agent_name = FEATURE_AGENT_MAP.get(normalized_feature)
        if agent_name and agent_name not in selected_agents:
            selected_agents.append(agent_name)
    return selected_agents


def normalize_requested_features(requested_features: list[str]) -> list[str]:
    return [
        str(feature).strip().lower()
        for feature in requested_features
        if str(feature).strip()
    ]


def extract_destination(user_request: str) -> str:
    matches = [
        (user_request.find(destination), destination)
        for destination in SUPPORTED_DESTINATIONS
        if destination in user_request
    ]
    if not matches:
        return "서울"
    return min(matches, key=lambda match: match[0])[1]


def extract_days(user_request: str) -> int:
    nights_days_match = re.search(r"(\d+)\s*박\s*(\d+)\s*일", user_request)
    if nights_days_match:
        return int(nights_days_match.group(2))

    days_match = re.search(r"(\d+)\s*일", user_request)
    if days_match:
        return int(days_match.group(1))

    nights_match = re.search(r"(\d+)\s*박", user_request)
    if nights_match:
        return int(nights_match.group(1)) + 1

    return 3


def resolve_agent_dir(agent_name: str) -> Path:
    internal_agent_dir = INTERNAL_AGENT_LIBRARY / agent_name
    if internal_agent_dir.exists():
        return internal_agent_dir
    return EXTERNAL_AGENT_LIBRARY / agent_name


def resolve_agent_source(agent_name: str) -> str:
    internal_agent_dir = INTERNAL_AGENT_LIBRARY / agent_name
    if internal_agent_dir.exists():
        return "internal"
    external_agent_dir_path = EXTERNAL_AGENT_LIBRARY / agent_name
    if external_agent_dir_path.exists():
        return "external"
    return "internal" if INTERNAL_AGENT_LIBRARY.exists() else "external"


def iter_agent_dirs():
    seen: set[str] = set()
    for source_name, root in [("internal", INTERNAL_AGENT_LIBRARY), ("external", EXTERNAL_AGENT_LIBRARY)]:
        if not root.exists():
            continue
        for path in sorted(root.iterdir(), key=lambda item: item.name):
            if (
                path.is_dir()
                and path.name.startswith("travel_")
                and path.name.endswith("_agent")
                and path.name not in seen
            ):
                seen.add(path.name)
                yield path, source_name


def build_input_data(payload: WorkflowRequest) -> dict[str, Any]:
    user_request = payload.user_request
    destination = payload.destination or extract_destination(user_request)
    location = payload.location or destination
    origin = payload.origin or ("현재 위치" if destination == "서울" else "서울")
    days = payload.days or extract_days(user_request)
    budget_level = payload.budget_level or ("low" if "저렴" in user_request else "medium")
    input_data: dict[str, Any] = {
        "user_request": user_request,
        "destination": destination,
        "location": location,
        "origin": origin,
        "days": days,
        "duration_days": days,
        "traveler_count": 1,
        "budget_level": budget_level,
        "budget": budget_level,
        "requested_features": payload.requested_features,
    }

    return input_data


def load_agent(agent_json_path: Path):
    with agent_json_path.open("r", encoding="utf-8") as file:
        metadata = json.load(file)

    agent_name = metadata["name"]
    entrypoint = agent_json_path.parent / metadata["entrypoint"]
    function_name = metadata["function"]
    module_name = f"{agent_name}_{uuid.uuid4().hex}"

    for cached_name in list(sys.modules):
        if cached_name == agent_name or cached_name.startswith(f"{agent_name}_"):
            sys.modules.pop(cached_name, None)

    spec = importlib.util.spec_from_file_location(module_name, entrypoint)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load agent entrypoint: {entrypoint}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise

    return metadata, getattr(module, function_name)


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _display_agent_path(agent_dir: Path) -> str:
    return str(agent_dir)


def _agent_library_item(agent_dir: Path, source: str) -> dict[str, Any]:
    agent_json_path = agent_dir / "agent.json"
    main_py_path = agent_dir / "main.py"
    readme_path = agent_dir / "README.md"
    has_agent_json = agent_json_path.exists()
    has_main_py = main_py_path.exists()
    has_readme = readme_path.exists()

    item: dict[str, Any] = {
        "name": agent_dir.name,
        "status": "missing_files",
        "path": _display_agent_path(agent_dir),
        "source": source,
        "has_agent_json": has_agent_json,
        "has_main_py": has_main_py,
        "has_readme": has_readme,
        "description": "",
        "role": "",
        "inputs": [],
        "outputs": [],
        "data_sources": [],
        "error": None,
    }

    if not has_agent_json or not has_main_py or not has_readme:
        missing_files = [
            filename
            for filename, exists in [
                ("agent.json", has_agent_json),
                ("main.py", has_main_py),
                ("README.md", has_readme),
            ]
            if not exists
        ]
        item["error"] = f"missing_files: {', '.join(missing_files)}"
        return item

    try:
        with agent_json_path.open("r", encoding="utf-8") as file:
            metadata = json.load(file)
    except Exception as exc:
        item["status"] = "invalid_agent_json"
        item["error"] = f"{type(exc).__name__}: {exc}"
        return item

    item.update({
        "name": str(metadata.get("name") or agent_dir.name),
        "status": "available",
        "source": source,
        "description": str(metadata.get("description") or ""),
        "role": str(metadata.get("role") or ""),
        "inputs": _as_list(metadata.get("inputs")),
        "outputs": _as_list(metadata.get("outputs")),
        "data_sources": _as_list(metadata.get("data_sources")),
    })
    return item


def get_agent_library() -> dict[str, Any]:
    agents = [_agent_library_item(agent_dir, source) for agent_dir, source in iter_agent_dirs()]
    source = "internal" if INTERNAL_AGENT_LIBRARY.exists() else "external"
    library_path = str(INTERNAL_AGENT_LIBRARY if INTERNAL_AGENT_LIBRARY.exists() else EXTERNAL_AGENT_LIBRARY)

    return {
        "library_path": library_path,
        "source": source,
        "library_mode": source,
        "total_agents": len(agents),
        "available_count": sum(1 for agent in agents if agent["status"] == "available"),
        "agents": agents,
    }


def run_workflow(payload: WorkflowRequest | str) -> dict[str, Any]:
    if isinstance(payload, str):
        workflow_request = WorkflowRequest(user_request=payload)
    else:
        workflow_request = payload

    user_request = workflow_request.user_request
    requested_features = normalize_requested_features(workflow_request.requested_features)
    routing_mode = "requested_features" if requested_features else "keyword_router"
    selected_agents_from_features = select_agents_from_features(requested_features) if requested_features else []
    if requested_features:
        selected_agents = selected_agents_from_features if selected_agents_from_features else ["travel_destination_agent"]
    else:
        selected_agents = select_agents(user_request)

    input_data = build_input_data(workflow_request)
    input_data_summary = {
        "destination": input_data["destination"],
        "location": input_data["location"],
        "origin": input_data["origin"],
        "days": input_data["days"],
        "budget_level": input_data["budget_level"],
        "requested_features": input_data["requested_features"],
    }
    routing_debug = {
        "routing_mode": routing_mode,
        "requested_features": input_data["requested_features"],
        "selected_agents_from_features": selected_agents_from_features,
        "selected_agents_final": selected_agents,
    }
    loaded_agents: list[dict[str, Any]] = []
    agent_results: list[dict[str, Any]] = []

    for agent_name in selected_agents:
        agent_dir = resolve_agent_dir(agent_name)
        try:
            metadata, run = load_agent(agent_dir / "agent.json")
            loaded_agents.append({
                "name": metadata["name"],
                "version": metadata["version"],
                "entrypoint": metadata["entrypoint"],
                "function": metadata["function"],
                "source": resolve_agent_source(agent_name),
            })
            agent_results.append(run(input_data))
        except Exception as exc:
            agent_results.append({
                "agent": agent_name,
                "data_source": "error",
                "summary": f"Failed to load or run {agent_name}.",
                "error": {
                    "type": type(exc).__name__,
                    "message": str(exc)
                }
            })

    agent_results, validation_report = validate_and_correct(input_data, agent_results)

    final_summary = "UI 선택값과 사용자 요청을 기준으로 필요한 에이전트를 선택하고, 선택된 에이전트의 결과를 통합했습니다."
    final_summary += f" 목적지는 {input_data['destination']} 기준입니다."
    if any(result.get("data_source") == "kma_api" for result in agent_results):
        final_summary += " 날씨 정보는 기상청 공공데이터 API 결과를 반영했습니다."
    if validation_report.get("status") == "corrected":
        final_summary += " 일부 결과는 자체검증 규칙에 따라 자동 보정되었습니다."

    return {
        "user_request": user_request,
        "input_data": input_data,
        "input_data_summary": input_data_summary,
        "routing_debug": routing_debug,
        "selected_agents": selected_agents,
        "loaded_agents": loaded_agents,
        "agent_results": agent_results,
        "validation_report": validation_report,
        "final_summary": final_summary
    }


@app.get("/")
def read_index() -> FileResponse:
    return FileResponse("static/index.html")


@app.get("/agent-library")
def agent_library_endpoint() -> dict[str, Any]:
    return get_agent_library()


@app.get("/health")
def health_endpoint() -> dict[str, Any]:
    agent_library = get_agent_library()
    return {
        "status": "ok",
        "app": "dynamic-agent-lab",
        "agent_source": "internal" if INTERNAL_AGENT_LIBRARY.exists() else "external_fallback",
        "agent_library_path": agent_library["library_path"],
        "available_agents": agent_library["available_count"],
        "env_loaded": {
            "KMA_SERVICE_KEY": bool(os.getenv("KMA_SERVICE_KEY")),
            "TOUR_API_SERVICE_KEY": bool(os.getenv("TOUR_API_SERVICE_KEY")),
        },
    }


@app.post("/run-workflow", response_model=WorkflowResponse)
def run_workflow_endpoint(payload: WorkflowRequest) -> dict[str, Any]:
    return run_workflow(payload)


if __name__ == "__main__":
    sample_request = "부산 2박 3일 여행지 추천하고 예산, 일정, 날씨, 관광지, 교통도 알려줘"
    print(json.dumps(run_workflow(sample_request), ensure_ascii=False, indent=2))
