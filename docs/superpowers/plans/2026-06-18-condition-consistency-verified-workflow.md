# 조건 정합 + 자기검증 워크플로우 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 에이전트 출력을 응답 직전 2단 게이트(규칙 + LLM 비평)로 검증해, 선택 조건과 무관/불일치한 카드를 제외하고 `verification_report`로 노출한다.

**Architecture:** 에이전트 실행·`validate_and_correct`는 그대로. 그 뒤 `validators/travel_verifier.py`(규칙, 결정적)로 정합성·관련성 필터 → `workflow_critic.py`(Anthropic Haiku, 선택적)로 비판적 keep/drop → `main.py`가 `verification_report` 조립. 키 없으면 `rule_only`로 graceful.

**Tech Stack:** FastAPI, Pydantic v2, pytest, anthropic SDK(lazy import), Vanilla JS.

스펙: `docs/superpowers/specs/2026-06-18-condition-consistency-verified-workflow-design.md`

---

## Phase A — 규칙 게이트 (LLM 없음)

### Task A1: `validators/travel_verifier.py`

**Files:** Create `validators/travel_verifier.py`, Create `tests/test_verifier.py`

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_verifier.py`:
```python
from validators.travel_verifier import verify_results

def _res(agent, **kw):
    d = {"agent": agent}; d.update(kw); return d

def test_day_trip_excludes_lodging():
    inp = {"destination": "속초", "days": 1, "travel_format": "당일치기"}
    kept, excluded = verify_results(inp, [_res("travel_lodging_agent", lodging_items=[]), _res("travel_food_agent")])
    assert "travel_lodging_agent" not in [k["agent"] for k in kept]
    assert any(e["reason"] == "day_trip_no_lodging" for e in excluded)

def test_schedule_day_mismatch_excluded():
    inp = {"destination": "속초", "days": 3, "travel_format": "자유여행"}
    kept, excluded = verify_results(inp, [_res("travel_schedule_agent", daily_itinerary=[{"day": 1}])])
    assert not kept and excluded[0]["reason"] == "schedule_day_mismatch"

def test_real_api_verified_mock_estimated():
    inp = {"destination": "제주", "days": 2}
    kept, _ = verify_results(inp, [_res("travel_weather_agent", data_source="kma_api"),
                                   _res("travel_food_agent", data_source="mock_plus_conditions")])
    st = {k["agent"]: k["verification"] for k in kept}
    assert st["travel_weather_agent"] == "verified" and st["travel_food_agent"] == "estimated"

def test_agent_error_excluded():
    kept, excluded = verify_results({"destination": "부산", "days": 2}, [_res("travel_tour_agent", data_source="error")])
    assert not kept and excluded[0]["reason"] == "agent_error"
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_verifier.py -q` → FAIL (모듈 없음).

- [ ] **Step 3: 구현** — `validators/travel_verifier.py`:
```python
REAL_API_SOURCE = {
    "travel_tour_agent": "tour_api",
    "travel_weather_agent": "kma_api",
    "travel_transport_agent": "odsay_api",
    "travel_destination_agent": "tour_api",
}


def _destination(input_data):
    return input_data.get("destination") or input_data.get("location")


def _days(input_data):
    try:
        return max(int(input_data.get("days") or input_data.get("duration_days") or 3), 1)
    except (TypeError, ValueError):
        return 3


def _parse_won(value):
    if value is None:
        return None
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return int(digits) if digits else None


def _status(result):
    a = result.get("agent")
    if a in REAL_API_SOURCE and result.get("data_source") == REAL_API_SOURCE[a]:
        return "verified"
    return "estimated"


def _exclusion_reason(result, input_data):
    """결정적 제외 사유를 반환(없으면 None). 필드가 없으면 관대하게(제외 안 함)."""
    a = result.get("agent")
    if result.get("data_source") == "error":
        return "agent_error"
    if input_data.get("travel_format") == "당일치기" and a == "travel_lodging_agent":
        return "day_trip_no_lodging"
    if a == "travel_schedule_agent":
        itin = result.get("daily_itinerary")
        if isinstance(itin, list) and len(itin) != _days(input_data):
            return "schedule_day_mismatch"
    if a == "travel_budget_agent":
        total = _parse_won(result.get("total"))
        if total is not None and total <= 0:
            return "budget_nonpositive"
    if a == "travel_destination_agent":
        dest, rd = _destination(input_data), result.get("destination")
        if dest and rd and dest not in str(rd) and str(rd) not in str(dest):
            return "destination_mismatch"
    return None


def verify_results(input_data, agent_results):
    """(kept, excluded) 반환. kept 각 항목에 'verification' 부여, excluded=[{agent,stage,reason}]."""
    kept, excluded = [], []
    for r in agent_results:
        if not isinstance(r, dict) or not r.get("agent"):
            continue
        reason = _exclusion_reason(r, input_data)
        if reason:
            excluded.append({"agent": r.get("agent"), "stage": "rule", "reason": reason})
            continue
        r = dict(r)
        r["verification"] = _status(r)
        kept.append(r)
    return kept, excluded
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_verifier.py -q` → PASS(4).

- [ ] **Step 5: 커밋**
```bash
git add validators/travel_verifier.py tests/test_verifier.py
git commit -m "feat(verify): rule-based relevance+consistency gate for agent results"
```

### Task A2: `main.py` 통합 + 응답 필드

**Files:** Modify `main.py`, Create `tests/test_verification_endpoint.py`

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_verification_endpoint.py`:
```python
from fastapi.testclient import TestClient
import main

client = TestClient(main.app)

BASE = {"user_request": "", "destination": "속초", "origin": "서울", "days": 3,
        "budget_level": "medium", "requested_features": ["budget", "schedule", "lodging"],
        "additional_conditions": {"themes": []}}

def _run(**over):
    r = client.post("/run-workflow", json={**BASE, **over})
    assert r.status_code == 200, r.text
    return r.json()

def test_response_has_verification_report():
    d = _run()
    assert "verification_report" in d
    assert d["verification_report"]["engine"] in ("rule_only", "rule+llm")

def test_day_trip_excludes_lodging_card():
    d = _run(travel_format="당일치기", days=3)
    assert all("lodging" not in r["agent"] for r in d["agent_results"])
    assert any(e["reason"] == "day_trip_no_lodging" for e in d["verification_report"]["excluded"])
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_verification_endpoint.py -q` → FAIL (verification_report 없음).

- [ ] **Step 3: 구현 — import** — `main.py`의 `from validators.travel_validator import validate_and_correct` 다음 줄에 추가:
```python
from validators.travel_verifier import verify_results
```

- [ ] **Step 4: 구현 — 응답 모델 필드** — `WorkflowResponse` 클래스의 `final_summary: str` 뒤에 추가:
```python
    verification_report: dict[str, Any] = Field(default_factory=dict)
```

- [ ] **Step 5: 구현 — run_workflow 게이트** — `run_workflow_endpoint`에서
```python
    res, report = validate_and_correct(input_data, results)
    input_data_summary = {"destination": dest, "days": days, "budget_level": input_data["budget_level"]}
```
를 다음으로 교체:
```python
    res, report = validate_and_correct(input_data, results)
    kept, excluded = verify_results(input_data, res)
    verification_report = {
        "engine": "rule_only",
        "excluded": excluded,
        "kept": [{"agent": k["agent"], "verification": k.get("verification")} for k in kept],
        "summary": (f"{len(excluded)}개 항목을 조건·정합성 기준으로 제외했습니다." if excluded
                    else "모든 항목이 조건에 정합합니다."),
    }
    res = kept
    input_data_summary = {"destination": dest, "days": days, "budget_level": input_data["budget_level"]}
```
그리고 `return {...}` 딕셔너리의 `"validation_report": report,` 다음에 추가:
```python
        "verification_report": verification_report,
```

- [ ] **Step 6: 통과 확인** — Run: `python -m pytest tests/test_verification_endpoint.py tests/ -q` → 전부 PASS.

- [ ] **Step 7: 커밋**
```bash
git add main.py tests/test_verification_endpoint.py
git commit -m "feat(workflow): apply rule verification gate, add verification_report to response"
```

---

## Phase B — LLM 비평 (Anthropic Haiku 4.5)

### Task B1: `workflow_critic.py` (순수 로직 + lazy 호출)

**Files:** Create `workflow_critic.py`, Create `tests/test_critic.py`

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_critic.py`:
```python
from workflow_critic import _parse_critique, critique

def test_parse_valid():
    raw = 'x {"keep":["a"],"drop":[{"agent":"b","reason":"무관"}],"final_summary":"s","match_notes":[]} y'
    p = _parse_critique(raw, {"a", "b"})
    assert p["keep"] == ["a"] and p["drop"][0]["agent"] == "b" and p["final_summary"] == "s"

def test_parse_invalid_returns_none():
    assert _parse_critique("not json", {"a"}) is None
    assert _parse_critique("", {"a"}) is None

def test_critique_applies_keep_drop():
    results = [{"agent": "a"}, {"agent": "b"}]
    fake = lambda prompt: '{"keep":["a"],"drop":[{"agent":"b","reason":"무관"}],"final_summary":"ok","match_notes":[]}'
    final, dropped, summary, engine = critique({}, results, _caller=fake)
    assert [r["agent"] for r in final] == ["a"]
    assert dropped[0]["agent"] == "b" and engine == "rule+llm" and summary == "ok"

def test_critique_fallback_when_no_result():
    results = [{"agent": "a"}]
    final, dropped, summary, engine = critique({}, results, _caller=lambda p: None)
    assert engine == "rule_only" and [r["agent"] for r in final] == ["a"] and dropped == []
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_critic.py -q` → FAIL (모듈 없음).

- [ ] **Step 3: 구현** — `workflow_critic.py`:
```python
import json
import os

MODEL = "claude-haiku-4-5"


def _build_prompt(conditions, results):
    cards = [{"agent": r.get("agent"), "summary": r.get("summary", ""), "verification": r.get("verification")}
             for r in results]
    return (
        "당신은 여행 설계 결과를 검증하는 비평가입니다. 아래 '선택 조건'에 비춰 각 결과 카드가 적합한지 "
        "비판적으로 판단하세요.\n"
        "규칙: 주어진 카드 중에서만 유지(keep)/제외(drop)를 정합니다. 새 항목을 만들지 마세요. "
        "조건과 무관하거나 모순되는 카드를 drop하고 한국어 사유를 답니다.\n"
        f"선택 조건: {json.dumps(conditions, ensure_ascii=False)}\n"
        f"결과 카드: {json.dumps(cards, ensure_ascii=False)}\n"
        'JSON만 출력: {"keep":["agent",...],"drop":[{"agent":"...","reason":"..."}],'
        '"final_summary":"...","match_notes":["..."]}'
    )


def _call_anthropic(prompt, timeout=8.0):
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key, timeout=timeout)
        msg = client.messages.create(model=MODEL, max_tokens=1024,
                                     messages=[{"role": "user", "content": prompt}])
        return "".join(getattr(b, "text", "") for b in msg.content if getattr(b, "type", None) == "text")
    except Exception:
        return None


def _parse_critique(raw, valid_agents):
    if not raw:
        return None
    try:
        data = json.loads(raw[raw.index("{"):raw.rindex("}") + 1])
    except (ValueError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or "keep" not in data:
        return None
    keep = [a for a in data.get("keep", []) if a in valid_agents]
    drop = [d for d in data.get("drop", []) if isinstance(d, dict) and d.get("agent") in valid_agents]
    return {"keep": keep, "drop": drop,
            "final_summary": data.get("final_summary", ""), "match_notes": data.get("match_notes", [])}


def critique(conditions, results, _caller=_call_anthropic):
    """(final_results, dropped, final_summary, engine). engine 'rule+llm' 성공, 'rule_only' fallback."""
    valid = {r.get("agent") for r in results}
    parsed = _parse_critique(_caller(_build_prompt(conditions, results)), valid)
    if not parsed:
        return results, [], "", "rule_only"
    keep = set(parsed["keep"]) or valid
    final = [r for r in results if r.get("agent") in keep]
    dropped = []
    reasons = {d["agent"]: d.get("reason", "") for d in parsed["drop"]}
    for r in results:
        a = r.get("agent")
        if a not in keep:
            dropped.append({"agent": a, "stage": "llm", "reason": reasons.get(a, "조건 관련성 낮음")})
    return final, dropped, parsed["final_summary"], "rule+llm"
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_critic.py -q` → PASS(4).

- [ ] **Step 5: 커밋**
```bash
git add workflow_critic.py tests/test_critic.py
git commit -m "feat(critic): LLM critique layer with graceful rule_only fallback"
```

### Task B2: 의존성 + 테스트 격리 + `main.py` 통합

**Files:** Modify `requirements.txt`, Create `tests/conftest.py`, Modify `main.py`, Modify `tests/test_verification_endpoint.py`

- [ ] **Step 1: 테스트 격리 — conftest** — `tests/conftest.py` 생성(모든 테스트를 오프라인=rule_only로):
```python
import pytest

@pytest.fixture(autouse=True)
def _no_anthropic(monkeypatch):
    # 테스트는 실제 LLM 호출 없이 결정적으로 동작(rule_only)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
```

- [ ] **Step 2: 실패 테스트 추가** — `tests/test_verification_endpoint.py` 끝에 추가:
```python
def test_engine_rule_only_without_key():
    # conftest가 키를 제거하므로 항상 rule_only
    d = _run()
    assert d["verification_report"]["engine"] == "rule_only"
```

- [ ] **Step 3: 실패 확인** — Run: `python -m pytest tests/test_verification_endpoint.py::test_engine_rule_only_without_key -q` → 현재는 통과(이미 rule_only). 통합 후에도 유지되는지 가드. (B2 통합으로 engine 분기 생기므로 회귀 가드 역할.)

- [ ] **Step 4: 의존성 추가** — `requirements.txt` 끝에 `anthropic` 추가. 그리고 설치:
```bash
python -m pip install anthropic
```

- [ ] **Step 5: 구현 — import** — `main.py`의 `from validators.travel_verifier import verify_results` 다음에:
```python
from workflow_critic import critique
```

- [ ] **Step 6: 구현 — run_workflow에 비평 적용** — A2에서 만든 블록을 다음으로 교체:
```python
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
```
그리고 `return` 딕셔너리의 `"final_summary"`를 비평 요약으로:
```python
        "final_summary": critic_summary or f"{dest} 여행 여정 설계 완료",
```

- [ ] **Step 7: 통과 확인** — Run: `python -m pytest tests/ -q` → 전부 PASS (격리로 rule_only).

- [ ] **Step 8: 커밋**
```bash
git add requirements.txt tests/conftest.py main.py tests/test_verification_endpoint.py
git commit -m "feat(workflow): integrate LLM critique stage (Haiku) with offline-safe tests"
```

---

## Phase C — UI 검증 요약 노출 + E2E

### Task C1: 검증 요약 블록 + 카드 배지

**Files:** Modify `static/index.html`, Modify `tests/test_ui_contract.py`

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_ui_contract.py` 끝에 추가:
```python
def test_ui_renders_verification_report():
    assert "verification_report" in HTML
    assert "function renderVerificationReport" in HTML
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_ui_contract.py -q` → FAIL.

- [ ] **Step 3: 구현 — 렌더 함수** — `static/index.html`의 `function displayWorkflowResult(data) {` 정의 바로 앞에 추가:
```javascript
      function renderVerificationReport(vr) {
        if (!vr || !vr.summary) return "";
        const excluded = vr.excluded || [];
        const exHtml = excluded.length
          ? `<details class="details-accordion" style="margin-top:12px;"><summary>제외된 항목 ${excluded.length}건</summary><div class="details-content">${excluded.map(e => `<p style="font-size:0.9rem;">• ${escapeHtml(e.agent)} <span style="color:var(--muted);">(${escapeHtml(e.stage)})</span> — ${escapeHtml(e.reason)}</p>`).join("")}</div></details>`
          : "";
        const engineLabel = vr.engine === "rule+llm" ? "규칙 + AI 비평" : "규칙 검증";
        return `<div style="border:1px solid var(--line); border-radius:var(--radius); padding:20px 25px; margin-bottom:40px; background:#fbfbfb;"><p class="search-field" style="margin-bottom:8px;">검증 요약 · ${escapeHtml(engineLabel)}</p><p style="font-size:1rem;">${escapeHtml(vr.summary)}</p>${exHtml}</div>`;
      }
```

- [ ] **Step 4: 구현 — displayWorkflowResult에 삽입** — `displayWorkflowResult`의
```javascript
        area.innerHTML = `<h1 style="font-weight:100; font-size:6rem; margin-bottom:120px; text-transform:uppercase; letter-spacing:-0.06em; text-align:center;">${escapeHtml(data.input_data.destination)}<br/>여행 설계</h1>` +
                         data.agent_results.filter(r => !r.agent.includes("planning")).map(renderAgentResult).join("");
```
를 다음으로 교체:
```javascript
        area.innerHTML = `<h1 style="font-weight:100; font-size:6rem; margin-bottom:120px; text-transform:uppercase; letter-spacing:-0.06em; text-align:center;">${escapeHtml(data.input_data.destination)}<br/>여행 설계</h1>` +
                         renderVerificationReport(data.verification_report) +
                         data.agent_results.filter(r => !r.agent.includes("planning")).map(renderAgentResult).join("");
```

- [ ] **Step 5: 구현 — 카드 검증 배지** — `renderAgentResult`의
```javascript
        const label = isP ? `<span class="customized-label">CUSTOMIZED</span>` : "";
```
를 다음으로 교체(검증 배지 추가):
```javascript
        const vmap = { verified: "✓ 검증", estimated: "⚠ 추정" };
        const vbadge = r.verification ? `<span class="customized-label" style="background:#f1f5f9; color:var(--text);">${vmap[r.verification] || r.verification}</span>` : "";
        const label = (isP ? `<span class="customized-label">CUSTOMIZED</span>` : "") + vbadge;
```

- [ ] **Step 6: 통과 확인** — Run: `python -m pytest tests/test_ui_contract.py -q` → PASS.

- [ ] **Step 7: 커밋**
```bash
git add static/index.html tests/test_ui_contract.py
git commit -m "feat(ui): show verification summary + per-card verified/estimated badge"
```

### Task C2: 전체 회귀 + 브라우저 E2E

- [ ] **Step 1: 전체 단위** — Run: `python -m pytest tests/ -q` → 전부 PASS.

- [ ] **Step 2: 서버 기동(깨끗한 포트)** — `python -m uvicorn main:app --host 127.0.0.1 --port 8028 > /tmp/uvicorn_8028.log 2>&1 &` 후 `/health` 확인.

- [ ] **Step 3: smoke** — Run: `BASE_URL=http://localhost:8028 python scripts/smoke_test.py` → 15/15.

- [ ] **Step 4: 브라우저 E2E(gstack)** — `B="$HOME/.claude/skills/gstack/browse/dist/browse"`:
  1. goto `http://127.0.0.1:8028/` → `wait --networkidle` → `console --errors` 0.
  2. "당일치기" 형태 선택(`#travel-format-select`=당일치기) + "미식 자유여행" 프리셋 또는 gourmet/foodie 테마 체크.
  3. `click #run-button` → `wait .result-card`.
  4. 숙박 카드 부재 확인: `js "Array.from(document.querySelectorAll('.result-card h2')).some(h=>h.textContent.includes('숙소'))"` → false.
  5. 검증 요약 노출 확인: `js "currentWorkflowResult.verification_report.engine"`, `js "currentWorkflowResult.verification_report.excluded.length"`.
  6. `screenshot /tmp/verified_workflow.png` → Read로 확인.
  - (로컬 `.env`에 키가 있으면 `engine`이 `rule+llm`, 없으면 `rule_only`. 둘 다 정상.)

- [ ] **Step 5: 프로덕션 메모** — `.env.example`에 `ANTHROPIC_API_KEY=your_anthropic_api_key_here` 추가(문서용). 커밋:
```bash
git add static/index.html .env.example
git commit -m "docs(env): document ANTHROPIC_API_KEY"
```

---

## 다음 단계 (별도)
- Vercel Production 환경변수 `ANTHROPIC_API_KEY` 추가 후 재배포(미적용 시 prod는 rule_only).
- 관련성 규칙 확장(테마별 결정적 제외)이 필요하면 `RELEVANCE_RULES` 테이블화.
