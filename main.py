import base64
import importlib.util
import json
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Any, List, Optional
from urllib.parse import quote

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from datetime import datetime

from validators.travel_validator import validate_and_correct
from validators.travel_verifier import verify_results
from workflow_critic import critique

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)

app = FastAPI(title="ONE'S OWN AI Travel Lab")
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Supabase 설정 (Direct API) ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

def _sb_call(method, url, **kwargs):
    # 네트워크/연결 오류는 무음 실패 대신 502로 표면화함.
    try:
        return method(url, **kwargs)
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Supabase 연결 오류: {e}")

def _sb_raise_for_status(resp):
    # PostgREST 에러 응답을 무음 {} 대신 실제 상태코드로 올림.
    if resp.ok:
        return
    try:
        body = resp.json()
    except ValueError:
        body = None
    detail = None
    if isinstance(body, dict):
        detail = body.get("message") or body.get("msg") or body.get("hint") or body.get("error_description")
    raise HTTPException(status_code=resp.status_code, detail=detail or (resp.text or "Supabase 요청 실패"))

class SupabaseClient:
    def __init__(self, url: str, key: str):
        self.url = url.rstrip("/")
        self.key = key
        self.headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    def auth_headers(self, user_token=None):
        # 사용자 JWT가 있으면 그 토큰으로 PostgREST를 호출해 RLS(auth.uid())가 적용되도록 함.
        if user_token:
            return {"apikey": self.key, "Authorization": f"Bearer {user_token}", "Content-Type": "application/json"}
        return self.headers
    def signup(self, email, password):
        resp = _sb_call(requests.post, f"{self.url}/auth/v1/signup", headers=self.headers, json={"email": email, "password": password})
        if not resp.ok: raise Exception(resp.json().get("msg") or resp.text)
        return resp.json()
    def login(self, email, password):
        resp = _sb_call(requests.post, f"{self.url}/auth/v1/token?grant_type=password", headers=self.headers, json={"email": email, "password": password})
        if not resp.ok: raise Exception(resp.json().get("error_description") or resp.text)
        return resp.json()
    def table(self, table_name, user_token=None): return SupabaseTable(self, table_name, user_token)

class SupabaseTable:
    def __init__(self, client, table_name, user_token=None):
        self.client = client
        self.table_url = f"{client.url}/rest/v1/{table_name}"
        self.headers = client.auth_headers(user_token)
    def select_all(self):
        resp = _sb_call(requests.get, f"{self.table_url}?order=created_at.desc", headers=self.headers)
        return resp.json() if resp.ok else []
    def select_mine(self):
        # RLS(USING auth.uid()=user_id)가 본인 행만 반환하므로 user_id 필터가 불필요함.
        resp = _sb_call(requests.get, f"{self.table_url}?order=created_at.desc", headers=self.headers)
        return resp.json() if resp.ok else []
    def insert(self, data):
        resp = _sb_call(requests.post, self.table_url, headers=self.headers, json=data)
        _sb_raise_for_status(resp)
        # PostgREST는 INSERT 성공 시 본문 없이 201을 반환할 수 있으므로 빈 본문을 허용함.
        try: return resp.json()
        except ValueError: return {"status": "success"}
    def patch(self, plan_id, data):
        resp = _sb_call(requests.patch, f"{self.table_url}?id=eq.{quote(str(plan_id), safe='')}", headers=self.headers, json=data)
        _sb_raise_for_status(resp)
        try: return resp.json()
        except ValueError: return {"status": "success"}
    def delete(self, item_id):
        resp = _sb_call(requests.delete, f"{self.table_url}?id=eq.{quote(str(item_id), safe='')}", headers=self.headers)
        _sb_raise_for_status(resp)
        return {"status": "success"}

sb: Optional[SupabaseClient] = None
if SUPABASE_URL and SUPABASE_ANON_KEY:
    sb = SupabaseClient(SUPABASE_URL, SUPABASE_ANON_KEY)

# --- 워크플로우 모델 ---
class Comment(BaseModel): user_name: str = "Anonymous"; content: str; user_id: Optional[str] = None
class Rating(BaseModel): score: int = Field(ge=1, le=5); comment: str | None = ""; user_id: Optional[str] = None
class SignupRequest(BaseModel): email: str; password: str
class LoginRequest(BaseModel): email: str; password: str
class TravelPlanSaveRequest(BaseModel): title: str; destination: str; content_json: dict
class TravelPlanUpdateRequest(BaseModel): title: Optional[str] = None; content_json: Optional[dict] = None

class RecommendRequest(BaseModel):
    budget_total: int
    people: int = 1
    days: int = 3
    themes: list[str] = Field(default_factory=list)
    origin: str | None = None

class WorkflowRequest(BaseModel):
    user_request: str
    destination: str | None = None
    location: str | None = None
    origin: str | None = None
    days: int | None = None
    people: int = 1
    travel_format: str = "자유여행"
    transport_mode: str | None = None
    pace: str = "보통"
    budget_level: str | None = None
    requested_features: list[str] = Field(default_factory=list)
    additional_conditions: dict[str, Any] = Field(default_factory=dict)

class WorkflowResponse(BaseModel):
    user_request: str; input_data: dict[str, Any]; input_data_summary: dict[str, Any]; selected_agents: list[str]; loaded_agents: list[dict[str, Any]]; agent_results: list[dict[str, Any]]; validation_report: dict[str, Any]; final_summary: str
    verification_report: dict[str, Any] = Field(default_factory=dict)

# --- 인증 토큰 처리 ---
def _bearer_token(authorization: Optional[str]) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    return authorization.split(" ", 1)[1].strip()

def _user_id_from_token(token: str) -> str:
    # JWT payload의 sub(=user_id) 추출. 토큰 자체의 유효성은 Supabase가 RLS에서 검증함.
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        sub = json.loads(base64.urlsafe_b64decode(payload.encode())).get("sub")
    except Exception:
        sub = None
    if not sub:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")
    return sub

# --- API 엔드포인트 ---
@app.post("/auth/signup")
async def signup(req: SignupRequest):
    if not sb: raise HTTPException(status_code=500, detail="Supabase Not Configured")
    try: return sb.signup(req.email, req.password)
    except HTTPException: raise  # 연결오류(502) 등은 그대로 표면화
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@app.post("/auth/login")
async def login(req: LoginRequest):
    if not sb: raise HTTPException(status_code=500, detail="Supabase Not Configured")
    try: return sb.login(req.email, req.password)
    except HTTPException: raise  # 연결오류(502) 등은 그대로 표면화
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/plans")
async def get_plans(authorization: Optional[str] = Header(default=None)):
    if not sb: raise HTTPException(status_code=503, detail="Supabase Not Configured")
    return sb.table("travel_plans", user_token=_bearer_token(authorization)).select_mine()

@app.post("/api/plans")
async def save_plan(plan: TravelPlanSaveRequest, authorization: Optional[str] = Header(default=None)):
    if not sb: raise HTTPException(status_code=503, detail="Supabase Not Configured")
    token = _bearer_token(authorization)
    user_id = _user_id_from_token(token)
    return sb.table("travel_plans", user_token=token).insert({"user_id": user_id, "title": plan.title, "destination": plan.destination, "content_json": plan.content_json})

@app.patch("/api/plans/{plan_id}")
async def update_plan(plan_id: str, plan: TravelPlanUpdateRequest, authorization: Optional[str] = Header(default=None)):
    if not sb: raise HTTPException(status_code=503, detail="Supabase Not Configured")
    token = _bearer_token(authorization)
    data = {"updated_at": datetime.now().isoformat()}
    if plan.title: data["title"] = plan.title
    if plan.content_json: data["content_json"] = plan.content_json
    return sb.table("travel_plans", user_token=token).patch(plan_id, data)

@app.delete("/api/plans/{plan_id}")
async def delete_plan(plan_id: str, authorization: Optional[str] = Header(default=None)):
    if not sb: raise HTTPException(status_code=503, detail="Supabase Not Configured")
    return sb.table("travel_plans", user_token=_bearer_token(authorization)).delete(plan_id)

@app.get("/comments")
def get_comments(): return sb.table("comments").select_all() if sb else []
@app.post("/comments")
def add_comment(c: Comment): return sb.table("comments").insert(c.model_dump()) if sb else {}
@app.get("/ratings")
def get_ratings():
    if not sb: return {"average": 0, "count": 0}
    items = sb.table("ratings").select_all()
    if not items: return {"average": 0, "count": 0}
    avg = round(sum(i["score"] for i in items)/len(items), 1)
    return {"average": avg, "count": len(items)}
@app.post("/ratings")
def add_rating(r: Rating): return sb.table("ratings").insert(r.model_dump()) if sb else {}

# --- 워크플로우 엔진 (RESTORED FROM e9a30ef) ---
SUPPORTED_DESTINATIONS = ["서울", "부산", "제주", "강릉", "전주", "대구", "대전", "광주", "인천", "여수", "경주", "속초", "춘천"]
FEATURE_AGENT_MAP = {
    "destination": "travel_destination_agent", "budget": "travel_budget_agent", "schedule": "travel_schedule_agent",
    "weather": "travel_weather_agent", "tour": "travel_tour_agent", "transport": "travel_transport_agent",
    "food": "travel_food_agent", "event": "travel_event_agent", "planning": "travel_planning_agent", "lodging": "travel_lodging_agent"
}
INTERNAL_AGENT_LIBRARY = BASE_DIR / "agents"
EXTERNAL_AGENT_LIBRARY = Path("D:/AI_AGENT_LIBRARY")

def resolve_agent_dir(name): return INTERNAL_AGENT_LIBRARY / name if (INTERNAL_AGENT_LIBRARY/name).exists() else EXTERNAL_AGENT_LIBRARY / name
def load_agent(p):
    with open(p, "r", encoding="utf-8") as f: meta = json.load(f)
    spec = importlib.util.spec_from_file_location(f"{meta['name']}_{uuid.uuid4().hex}", p.parent / meta["entrypoint"])
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return meta, getattr(mod, meta["function"])

@app.post("/run-workflow", response_model=WorkflowResponse)
def run_workflow_endpoint(payload: WorkflowRequest):
    req = payload.user_request
    dest = payload.destination or next((d for d in SUPPORTED_DESTINATIONS if d in req), "서울")
    days = payload.days or 3
    if payload.travel_format == "당일치기":
        days = 1
    features = payload.requested_features or ["planning", "destination", "weather", "transport", "budget", "food", "tour", "schedule", "lodging"]

    # 순서 고정 및 에이전트 선별 (연결성 보장)
    base_order = ["travel_planning_agent", "travel_destination_agent", "travel_weather_agent", "travel_transport_agent", "travel_budget_agent",
                  "travel_tour_agent", "travel_food_agent", "travel_event_agent", "travel_lodging_agent"]
    
    selected_from_features = [FEATURE_AGENT_MAP[f] for f in features if f in FEATURE_AGENT_MAP]
    selected = ["travel_planning_agent"]
    for name in base_order:
        if name in selected_from_features and name not in selected: selected.append(name)
    if "travel_schedule_agent" in selected_from_features or "schedule" in features: selected.append("travel_schedule_agent")
    
    input_data = {
        # 사용자 추가 조건(themes/companions/priority 등)을 먼저 펼치되,
        # 아래 확정 입력이 마지막에 이겨 destination/days/people 등을 덮어쓰지 못하게 한다.
        **payload.additional_conditions,
        "user_request": req, "destination": dest, "origin": payload.origin or "서울", "days": days,
        "duration_days": days, "people": max(payload.people, 1), "budget_level": payload.budget_level or "medium", "requested_features": features,
        "travel_format": payload.travel_format, "transport_mode": payload.transport_mode, "pace": payload.pace,
    }

    if "family_kids" in (input_data.get("themes") or []):
        _comps = list(input_data.get("companions") or [])
        if "family" not in _comps:
            _comps.append("family")
        input_data["companions"] = _comps

    results, loaded = [], []
    for name in selected:
        try:
            m, run_func = load_agent(resolve_agent_dir(name) / "agent.json")
            loaded.append({"name": name, "status": "available"})
            
            # [연결성의 핵심] 모든 이전 에이전트의 결과를 실시간으로 공유
            input_data["agent_results"] = results
            input_data["agent_results_by_agent"] = {r.get("agent"): r for r in results if isinstance(r, dict) and r.get("agent")}
            
            results.append(run_func(input_data))
        except Exception as e:
            results.append({"agent": name, "summary": f"설계 오류: {e}", "data_source": "error"})
    
    res, report = validate_and_correct(input_data, results)
    kept, excluded = verify_results(input_data, res)
    conditions = {k: input_data.get(k) for k in
                  ("destination", "origin", "days", "budget_level", "travel_format", "transport_mode", "pace", "themes")}
    final, dropped, critic_summary, engine = critique(conditions, kept)
    verification_report = {
        "engine": engine,
        "excluded": excluded + dropped,
        "kept": [{"agent": k["agent"], "verification": k.get("verification")} for k in final],
        "summary": (critic_summary or (f"{len(excluded) + len(dropped)}개 항목을 조건·정합성 기준으로 제외했습니다."
                                       if (excluded or dropped) else "모든 항목이 조건에 정합합니다.")),
    }
    res = final
    input_data_summary = {"destination": dest, "days": days, "budget_level": input_data["budget_level"]}
    
    return {
        "user_request": req, "input_data": input_data, "input_data_summary": input_data_summary, 
        "selected_agents": selected, "loaded_agents": loaded, "agent_results": res, 
        "validation_report": report, "final_summary": critic_summary or f"{dest} 여행 여정 설계 완료",
        "verification_report": verification_report
    }

@app.post("/recommend")
def recommend_endpoint(payload: RecommendRequest):
    _, run_func = load_agent(resolve_agent_dir("travel_recommender_agent") / "agent.json")
    result = run_func({
        "budget_total": payload.budget_total,
        "people": payload.people,
        "days": payload.days,
        "themes": payload.themes,
        "origin": payload.origin or "서울",
        "candidates": SUPPORTED_DESTINATIONS,
    })
    return {"input_echo": payload.model_dump(), **result}

@app.get("/agent-library")
def lib(): return {"agents": [{"name": d.name, "status": "available"} for d in INTERNAL_AGENT_LIBRARY.iterdir() if d.is_dir()], "available_count": 10, "total_agents": 10}
@app.get("/feature-map")
def feat(): return {"features": FEATURE_AGENT_MAP, "feature_count": len(FEATURE_AGENT_MAP)}
@app.get("/health")
def health(): return {"status": "ok", "available_agents": 10, "supabase": "Initialized" if sb else "Not Configured"}
@app.get("/")
def home(): return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8013)
