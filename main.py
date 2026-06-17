import importlib.util
import json
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Any, List, Optional

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from datetime import datetime

from validators.travel_validator import validate_and_correct

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)

app = FastAPI(title="dynamic-agent-lab")
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Supabase 설정 (Direct API 방식) ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

class SupabaseClient:
    def __init__(self, url: str, key: str):
        self.url = url.rstrip("/")
        self.key = key
        self.headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    
    def signup(self, email, password):
        resp = requests.post(f"{self.url}/auth/v1/signup", headers=self.headers, json={"email": email, "password": password})
        if not resp.ok: raise Exception(resp.json().get("msg") or resp.text)
        return resp.json()
    
    def login(self, email, password):
        resp = requests.post(f"{self.url}/auth/v1/token?grant_type=password", headers=self.headers, json={"email": email, "password": password})
        if not resp.ok: raise Exception(resp.json().get("error_description") or resp.text)
        return resp.json()
    
    def table(self, table_name): return SupabaseTable(self, table_name)

class SupabaseTable:
    def __init__(self, client, table_name):
        self.client = client
        self.table_url = f"{client.url}/rest/v1/{table_name}"
    
    def select_all(self):
        resp = requests.get(f"{self.table_url}?order=created_at.desc", headers=self.client.headers)
        return resp.json() if resp.ok else []

    def select_by_user(self, user_id):
        resp = requests.get(f"{self.table_url}?user_id=eq.{user_id}&order=created_at.desc", headers=self.client.headers)
        return resp.json() if resp.ok else []
    
    def insert(self, data):
        resp = requests.post(self.table_url, headers=self.client.headers, json=data)
        return resp.json() if resp.ok else {}
    
    def update(self, item_id, user_id, data):
        resp = requests.patch(f"{self.table_url}?id=eq.{item_id}&user_id=eq.{user_id}", headers=self.client.headers, json=data)
        return resp.json() if resp.ok else {}
    
    def delete(self, item_id, user_id):
        resp = requests.delete(f"{self.table_url}?id=eq.{item_id}&user_id=eq.{user_id}", headers=self.client.headers)
        return {"status": "success"} if resp.ok else {"status": "error"}

sb: Optional[SupabaseClient] = None
supabase_status = "Not Configured"
if SUPABASE_URL and SUPABASE_ANON_KEY:
    sb = SupabaseClient(SUPABASE_URL, SUPABASE_ANON_KEY)
    supabase_status = "Initialized"

# --- 데이터 모델 ---
class Comment(BaseModel): user_name: str = "Anonymous"; content: str; user_id: Optional[str] = None
class Rating(BaseModel): score: int = Field(ge=1, le=5); comment: str | None = ""; user_id: Optional[str] = None
class SignupRequest(BaseModel): email: str; password: str
class LoginRequest(BaseModel): email: str; password: str
class TravelPlanSaveRequest(BaseModel): title: str; destination: str; content_json: dict
class TravelPlanUpdateRequest(BaseModel): title: Optional[str] = None; content_json: Optional[dict] = None

# --- Auth & Plan API (Supabase 연동) ---
@app.post("/auth/signup")
async def signup(req: SignupRequest):
    if not sb: raise HTTPException(status_code=500)
    try: return sb.signup(req.email, req.password)
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@app.post("/auth/login")
async def login(req: LoginRequest):
    if not sb: raise HTTPException(status_code=500)
    try: return sb.login(req.email, req.password)
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/plans")
async def get_plans(user_id: str): return sb.table("travel_plans").select_by_user(user_id) if sb else []

@app.post("/api/plans")
async def save_plan(user_id: str, plan: TravelPlanSaveRequest):
    if not sb: raise HTTPException(status_code=500)
    return sb.table("travel_plans").insert({"user_id": user_id, "title": plan.title, "destination": plan.destination, "content_json": plan.content_json})

@app.patch("/api/plans/{plan_id}")
async def update_plan(plan_id: str, user_id: str, plan: TravelPlanUpdateRequest):
    if not sb: raise HTTPException(status_code=500)
    data = {"updated_at": datetime.now().isoformat()}
    if plan.title: data["title"] = plan.title
    if plan.content_json: data["content_json"] = plan.content_json
    return sb.table("travel_plans").update(plan_id, user_id, data)

@app.delete("/api/plans/{plan_id}")
async def delete_plan(plan_id: str, user_id: str):
    if not sb: raise HTTPException(status_code=500)
    return sb.table("travel_plans").delete(plan_id, user_id)

# --- 통합 댓글 및 평가 API (Supabase 연동) ---
@app.get("/comments")
def get_comments_endpoint():
    return sb.table("comments").select_all() if sb else []

@app.post("/comments")
def add_comment_endpoint(c: Comment):
    if not sb: raise HTTPException(status_code=500)
    return sb.table("comments").insert(c.dict())

@app.get("/ratings")
def get_ratings_endpoint():
    if not sb: return {"average": 0, "count": 0}
    items = sb.table("ratings").select_all()
    if not items: return {"average": 0, "count": 0}
    avg = round(sum(i["score"] for i in items)/len(items), 1)
    return {"average": avg, "count": len(items)}

@app.post("/ratings")
def add_rating_endpoint(r: Rating):
    if not sb: raise HTTPException(status_code=500)
    return sb.table("ratings").insert(r.dict())

# --- 워크플로우 엔진 ---
class WorkflowRequest(BaseModel):
    user_request: str
    destination: str | None = None
    location: str | None = None
    origin: str | None = None
    days: int | None = None
    budget_level: str | None = None
    requested_features: list[str] = Field(default_factory=list)
    additional_conditions: dict[str, Any] = Field(default_factory=dict)

class WorkflowResponse(BaseModel):
    user_request: str; input_data: dict[str, Any]; input_data_summary: dict[str, Any]; selected_agents: list[str]; loaded_agents: list[dict[str, Any]]; agent_results: list[dict[str, Any]]; validation_report: dict[str, Any]; final_summary: str

SUPPORTED_DESTINATIONS = ["서울", "부산", "제주", "강릉", "전주", "대구", "대전", "광주", "인천", "여수", "경주", "속초", "춘천"]
FEATURE_AGENT_MAP = { "destination": "travel_destination_agent", "budget": "travel_budget_agent", "schedule": "travel_schedule_agent", "weather": "travel_weather_agent", "tour": "travel_tour_agent", "transport": "travel_transport_agent", "food": "travel_food_agent", "event": "travel_event_agent", "planning": "travel_planning_agent", "lodging": "travel_lodging_agent" }
INTERNAL_AGENT_LIBRARY = BASE_DIR / "agents"
EXTERNAL_AGENT_LIBRARY = Path("D:/AI_AGENT_LIBRARY")

def resolve_agent_dir(name):
    d = INTERNAL_AGENT_LIBRARY / name
    return d if d.exists() else EXTERNAL_AGENT_LIBRARY / name

def load_agent(p):
    with open(p, "r", encoding="utf-8") as f: meta = json.load(f)
    spec = importlib.util.spec_from_file_location(f"{meta['name']}_{uuid.uuid4().hex}", p.parent / meta["entrypoint"])
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return meta, getattr(mod, meta["function"])

@app.get("/agent-library")
def agent_library():
    agents = []
    for root in [INTERNAL_AGENT_LIBRARY, EXTERNAL_AGENT_LIBRARY]:
        if not root.exists(): continue
        for d in root.iterdir():
            if d.is_dir() and d.name.endswith("_agent") and (d / "agent.json").exists():
                with open(d / "agent.json", "r", encoding="utf-8") as f: m = json.load(f)
                agents.append({"name": m["name"], "status": "available"})
    return {"agents": agents, "total_agents": len(agents), "available_count": len(agents)}

@app.get("/feature-map")
def feature_map(): return {"features": FEATURE_AGENT_MAP, "feature_count": len(FEATURE_AGENT_MAP)}

@app.get("/health")
def health(): return {"status": "ok", "available_agents": 10, "supabase": supabase_status}

@app.post("/run-workflow", response_model=WorkflowResponse)
def run_workflow_endpoint(payload: WorkflowRequest):
    req = payload.user_request
    dest = payload.destination or next((d for d in SUPPORTED_DESTINATIONS if d in req), "서울")
    days = payload.days or 3
    features = payload.requested_features or ["planning", "weather", "transport", "budget", "food", "tour", "schedule"]
    
    selected = [FEATURE_AGENT_MAP[f] for f in features if f in FEATURE_AGENT_MAP]
    if "travel_planning_agent" not in selected: selected.insert(0, "travel_planning_agent")
    
    input_data = { "user_request": req, "destination": dest, "origin": payload.origin or "서울", "days": days, "budget_level": payload.budget_level or "medium", "requested_features": features, **payload.additional_conditions }
    
    results, loaded = [], []
    for name in selected:
        try:
            m, run = load_agent(resolve_agent_dir(name) / "agent.json")
            loaded.append({"name": name, "status": "available"})
            input_data["agent_results"] = results
            input_data["agent_results_by_agent"] = {r["agent"]: r for r in results if "agent" in r}
            results.append(run(input_data))
        except Exception as e: results.append({"agent": name, "summary": f"Error: {e}", "data_source": "error"})
    
    res, report = validate_and_correct(input_data, results)
    input_data_summary = { "destination": dest, "days": days, "budget_level": input_data["budget_level"] }
    return {"user_request": req, "input_data": input_data, "input_data_summary": input_data_summary, "selected_agents": selected, "loaded_agents": loaded, "agent_results": res, "validation_report": report, "final_summary": f"Plan for {dest} is ready."}

@app.get("/")
def home(): return FileResponse("static/index.html")
