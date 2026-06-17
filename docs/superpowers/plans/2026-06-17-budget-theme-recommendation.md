# 예산·테마 여행 추천 시스템 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 총 예산·인원·일수·테마를 입력하면 맞는 목적지 후보 5개를 예상 총비용·테마 매칭과 함께 추천하는 기능을 추가한다.

**Architecture:** 예산 계산 로직을 공용 모듈 `budget_model.py`로 추출(인원·일수 반영)하고, 기존 `travel_budget_agent`와 신규 `travel_recommender_agent`가 공유한다. 추천은 `POST /recommend`로 노출하고, 프런트에 입력 패널/결과 카드를 추가한다.

**Tech Stack:** Python 3.11, FastAPI, pytest(신규), 기존 동적 에이전트 로더(importlib).

스펙: `docs/superpowers/specs/2026-06-17-budget-theme-recommendation-design.md`

---

## File Structure

- Create `budget_model.py` (root) — 단가표 + `estimate_budget()` (인원/일수/객실 규칙). 단일 책임: 예산 추정.
- Modify `agents/travel_budget_agent/main.py` — 자체 계산을 `budget_model` 호출로 교체(동작 보존, people 반영).
- Create `agents/travel_recommender_agent/agent.json` + `main.py` — 목적지 점수화/추천.
- Modify `main.py` — `RecommendRequest` 모델 + `POST /recommend`.
- Modify `static/index.html` — 추천 입력 패널 + 결과 렌더.
- Create `tests/test_budget_model.py`, `tests/test_recommender.py` — 단위 테스트.
- Modify `requirements.txt` — pytest 추가(dev).
- Modify `scripts/smoke_test.py` — `/recommend` smoke(있으면 추가).

---

### Task 0: 테스트 환경 준비

**Files:**
- Create: `tests/__init__.py` (빈 파일)
- Modify: `requirements.txt`

- [ ] **Step 1: pytest 설치**

Run: `pip install pytest`
Expected: `Successfully installed pytest-...`

- [ ] **Step 2: tests 패키지 생성**

Create empty file `tests/__init__.py`.

- [ ] **Step 3: requirements.txt에 pytest 추가**

`requirements.txt` 끝에 한 줄 추가:
```
pytest
```

- [ ] **Step 4: Commit**

```bash
git add requirements.txt tests/__init__.py
git commit -m "chore: add pytest for unit tests"
```

---

### Task 1: 공용 예산 모델 `budget_model.py`

**Files:**
- Create: `budget_model.py`
- Test: `tests/test_budget_model.py`

- [ ] **Step 1: 실패하는 테스트 작성**

Create `tests/test_budget_model.py`:
```python
from budget_model import estimate_budget


def test_single_person_matches_legacy_seoul_busan():
    # 1인 기본: 기존 budget 에이전트와 동일한 셈법이어야 한다(회귀 방지).
    r = estimate_budget("서울", "부산", days=3, level="medium", people=1)
    eb = r["estimated_budget"]
    # 식비: 18000 * (3*3-1=8) * 1 = 144,000
    assert eb["food"] == 144000
    # 숙박: 100000 * 2박 * 1실 = 200,000
    assert eb["accommodation"] == 200000
    assert r["total"] == eb["total"]


def test_scales_with_people_and_rooms():
    one = estimate_budget("서울", "부산", days=3, level="medium", people=1)["total"]
    four = estimate_budget("서울", "부산", days=3, level="medium", people=4)["total"]
    # 4인이면 식비/교통/체험은 4배, 숙박은 2실 → 총액이 1인보다 크게 증가
    assert four > one * 2


def test_rooms_ceil_half_people():
    # 3인 → 2실
    three = estimate_budget("서울", "제주", days=2, level="low", people=3)["estimated_budget"]
    two = estimate_budget("서울", "제주", days=2, level="low", people=2)["estimated_budget"]
    assert three["accommodation"] == two["accommodation"]  # 둘 다 2실


def test_invalid_level_falls_back_medium():
    r = estimate_budget("서울", "부산", days=1, level="bogus", people=1)
    assert r["total"] > 0
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_budget_model.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'budget_model'`

- [ ] **Step 3: 최소 구현 작성**

Create `budget_model.py`:
```python
import math

BUDGET_UNIT_PRICES = {
    "low":    {"meal_per_count": 10000, "lodging_per_night": 60000,  "local_transport_per_day": 12000, "tour_event_per_day": 10000, "buffer_rate": 0.08},
    "medium": {"meal_per_count": 18000, "lodging_per_night": 100000, "local_transport_per_day": 20000, "tour_event_per_day": 25000, "buffer_rate": 0.10},
    "high":   {"meal_per_count": 30000, "lodging_per_night": 180000, "local_transport_per_day": 35000, "tour_event_per_day": 50000, "buffer_rate": 0.15},
}

LONG_DISTANCE_TRANSPORT = {
    ("서울", "부산"): {"low": 60000, "medium": 120000, "high": 180000},
    ("서울", "제주"): {"low": 120000, "medium": 220000, "high": 350000},
    ("부산", "제주"): {"low": 100000, "medium": 180000, "high": 300000},
}
DEFAULT_LONG_DISTANCE_TRANSPORT = {"low": 50000, "medium": 90000, "high": 150000}


def _safe_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _round_krw(amount):
    return int(round(float(amount) / 1000) * 1000)


def estimate_budget(origin, destination, days, level, people=1, themes=None, companions=None, priority=None):
    """예상 경비를 정수(원)로 반환. people 기본 1 → 기존 1인 셈법과 동일."""
    themes = themes or []
    companions = companions or []
    level = str(level or "medium").lower()
    if level not in BUDGET_UNIT_PRICES:
        level = "medium"
    people = max(_safe_int(people, 1), 1)
    days = max(_safe_int(days, 1), 1)

    unit = BUDGET_UNIT_PRICES[level].copy()
    if "activity" in themes:
        unit["tour_event_per_day"] *= 1.5
    if "family" in companions:
        unit["buffer_rate"] += 0.05
    if priority == "quality":
        unit["meal_per_count"] *= 1.2

    nights = max(days - 1, 0)
    meal_count = days * 3 - 1 if days > 1 else 2
    rooms = math.ceil(people / 2)

    route = (origin, destination)
    long_dist = (LONG_DISTANCE_TRANSPORT.get(route) or DEFAULT_LONG_DISTANCE_TRANSPORT)[level]

    transport = _round_krw((long_dist + unit["local_transport_per_day"] * days) * people)
    lodging = _round_krw(unit["lodging_per_night"] * nights * rooms)
    food = _round_krw(unit["meal_per_count"] * meal_count * people)
    activities = _round_krw(unit["tour_event_per_day"] * days * people)

    subtotal = transport + lodging + food + activities
    buffer = _round_krw(subtotal * unit["buffer_rate"])
    total = _round_krw(subtotal + buffer)

    return {
        "estimated_budget": {
            "transportation": transport,
            "accommodation": lodging,
            "food": food,
            "activities": activities,
            "buffer": buffer,
            "total": total,
        },
        "total": total,
    }
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_budget_model.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add budget_model.py tests/test_budget_model.py
git commit -m "feat: add shared budget_model (people/days/rooms aware)"
```

---

### Task 2: 기존 budget 에이전트가 공용 모델 사용

**Files:**
- Modify: `agents/travel_budget_agent/main.py`

- [ ] **Step 1: 회귀 확인 테스트 작성** (`tests/test_budget_agent.py`)

Create `tests/test_budget_agent.py`:
```python
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_agent():
    p = ROOT / "agents" / "travel_budget_agent" / "main.py"
    spec = importlib.util.spec_from_file_location("budget_agent_under_test", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_budget_agent_returns_formatted_total():
    mod = _load_agent()
    out = mod.run({"origin": "서울", "destination": "부산", "days": 3, "budget_level": "medium"})
    assert out["agent"] == "travel_budget_agent"
    assert out["total"].endswith("원")
    assert out["estimated_budget"]["food"] == "144,000원"  # 1인 기준 유지


def test_budget_agent_people_scales():
    mod = _load_agent()
    out = mod.run({"origin": "서울", "destination": "부산", "days": 3, "budget_level": "medium", "people": 4})
    assert out["estimated_budget"]["food"] == "576,000원"  # 144,000 * 4
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_budget_agent.py -v`
Expected: `test_budget_agent_people_scales` FAIL (현재 people 미반영 → 144,000원 그대로)

- [ ] **Step 3: budget 에이전트 리팩터링**

Replace the entire contents of `agents/travel_budget_agent/main.py` with:
```python
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from budget_model import estimate_budget


def run(input_data):
    safe_input = input_data if isinstance(input_data, dict) else {}
    destination = safe_input.get("destination") or "부산"
    origin = safe_input.get("origin") or "서울"
    days = safe_input.get("days", 3)
    budget_level = str(safe_input.get("budget_level") or "medium").lower()
    people = safe_input.get("people", 1)

    companions = safe_input.get("companions", [])
    themes = safe_input.get("themes", [])
    priority = safe_input.get("priority", "")

    result = estimate_budget(origin, destination, days, budget_level,
                             people=people, themes=themes, companions=companions, priority=priority)
    eb = result["estimated_budget"]
    total = result["total"]

    summary = f"{budget_level.upper()} 수준의 예산 설계입니다. "
    if "family" in companions:
        summary += "아이와 함께하는 여행을 위해 여유로운 예비비를 책정했습니다. "
    if "activity" in themes:
        summary += "액티비티 중심의 일정을 위해 체험비를 상향 조정했습니다."

    return {
        "agent": "travel_budget_agent",
        "data_source": "mock_plus_conditions",
        "total": f"{total:,}원",
        "summary": summary,
        "estimated_budget": {
            "transportation": f"{eb['transportation']:,}원",
            "accommodation": f"{eb['accommodation']:,}원",
            "food": f"{eb['food']:,}원",
            "activities": f"{eb['activities']:,}원",
            "buffer": f"{eb['buffer']:,}원",
            "total": f"{eb['total']:,}원",
        },
        "debug_info": {"companions": companions, "themes": themes, "priority": priority},
    }
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_budget_agent.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: 통합 회귀 확인 (앱 임포트)**

Run: `python -c "import main; print('ok')"`
Expected: `ok`

- [ ] **Step 6: Commit**

```bash
git add agents/travel_budget_agent/main.py tests/test_budget_agent.py
git commit -m "refactor: budget agent uses shared budget_model with people support"
```

---

### Task 3: 추천 에이전트 `travel_recommender_agent`

**Files:**
- Create: `agents/travel_recommender_agent/agent.json`
- Create: `agents/travel_recommender_agent/main.py`
- Test: `tests/test_recommender.py`

- [ ] **Step 1: 실패하는 테스트 작성**

Create `tests/test_recommender.py`:
```python
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    p = ROOT / "agents" / "travel_recommender_agent" / "main.py"
    spec = importlib.util.spec_from_file_location("recommender_under_test", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_returns_at_most_limit():
    mod = _load()
    out = mod.run({"budget_total": 1000000, "people": 2, "days": 3, "themes": ["healing"], "limit": 5})
    assert out["agent"] == "travel_recommender_agent"
    assert len(out["recommendations"]) <= 5


def test_within_budget_sorted_first():
    mod = _load()
    out = mod.run({"budget_total": 2000000, "people": 2, "days": 2, "themes": ["culture"]})
    recs = out["recommendations"]
    flags = [r["within_budget"] for r in recs]
    # within_budget=True 후보가 False보다 앞에 온다
    assert flags == sorted(flags, reverse=True)


def test_theme_match_recorded():
    mod = _load()
    out = mod.run({"budget_total": 3000000, "people": 1, "days": 2, "themes": ["culture"],
                   "candidates": ["경주", "부산"]})
    rec_gyeongju = next(r for r in out["recommendations"] if r["destination"] == "경주")
    assert "culture" in rec_gyeongju["matched_themes"]


def test_tiny_budget_marks_over():
    mod = _load()
    out = mod.run({"budget_total": 1000, "people": 2, "days": 3, "themes": []})
    assert all(r["within_budget"] is False for r in out["recommendations"])
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_recommender.py -v`
Expected: FAIL — 파일 없음 (`No such file or directory` / import error)

- [ ] **Step 3: agent.json 작성**

Create `agents/travel_recommender_agent/agent.json`:
```json
{
  "name": "travel_recommender_agent",
  "description": "총 예산·인원·일수·테마를 입력받아 적합한 목적지 후보를 예상 총비용과 함께 추천하는 에이전트입니다.",
  "role": "예산/테마 기반 목적지 추천",
  "inputs": ["budget_total", "people", "days", "themes", "origin", "candidates"],
  "outputs": ["summary", "recommendations", "data_source", "debug_info"],
  "env_vars": [],
  "version": "0.1.0",
  "entrypoint": "main.py",
  "function": "run"
}
```

- [ ] **Step 4: 추천 에이전트 구현**

Create `agents/travel_recommender_agent/main.py`:
```python
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from budget_model import estimate_budget

DESTINATION_PROFILES = {
    "서울": ["culture", "foodie", "photo"],
    "부산": ["activity", "foodie", "photo"],
    "제주": ["healing", "activity", "photo"],
    "강릉": ["healing", "activity", "photo"],
    "전주": ["foodie", "culture"],
    "대구": ["foodie", "culture"],
    "대전": ["culture", "foodie"],
    "광주": ["culture", "foodie"],
    "인천": ["activity", "foodie", "photo"],
    "여수": ["healing", "foodie", "photo"],
    "경주": ["culture", "photo", "healing"],
    "속초": ["healing", "activity", "foodie"],
    "춘천": ["healing", "photo", "foodie"],
}

LEVEL_LABEL = {"low": "알뜰하게", "medium": "적당하게", "high": "넉넉하게"}


def _safe_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _affordable(origin, dest, days, people, budget_total, themes):
    """예산 내 최고 수준(level, total)과 low 기준 total을 반환."""
    best = None
    for lvl in ("low", "medium", "high"):
        total = estimate_budget(origin, dest, days, lvl, people=people, themes=themes)["total"]
        if total <= budget_total:
            best = (lvl, total)
    low_total = estimate_budget(origin, dest, days, "low", people=people, themes=themes)["total"]
    return best, low_total


def _reason(dest, matched, within, lvl, people, days):
    parts = []
    if matched:
        parts.append(f"{', '.join(matched)} 테마에 잘 맞고")
    if within:
        parts.append(f"{people}인 {days}일 예산 안에서 '{LEVEL_LABEL.get(lvl, lvl)}' 수준으로 다녀올 수 있습니다")
    else:
        parts.append("입력하신 예산으로는 다소 빠듯합니다")
    return f"{dest}: " + ", ".join(parts) + "."


def run(input_data):
    safe = input_data if isinstance(input_data, dict) else {}
    budget_total = max(_safe_int(safe.get("budget_total"), 0), 0)
    people = max(_safe_int(safe.get("people"), 1), 1)
    days = max(_safe_int(safe.get("days"), 1), 1)
    themes = safe.get("themes") or []
    origin = safe.get("origin") or "서울"
    limit = max(_safe_int(safe.get("limit"), 5), 1)
    pool = safe.get("candidates") or list(DESTINATION_PROFILES.keys())

    recs = []
    for dest in pool:
        if dest == origin:
            continue
        best, low_total = _affordable(origin, dest, days, people, budget_total, themes)
        within = best is not None
        profile = DESTINATION_PROFILES.get(dest, [])
        matched = [t for t in themes if t in profile]
        theme_fit = (len(matched) / len(themes)) if themes else 0.5

        if within:
            lvl, est = best
            headroom = max(0.0, min(1.0, (budget_total - est) / budget_total)) if budget_total else 0.0
        else:
            lvl, est = None, low_total
            headroom = 0.0

        budget_fit = 1.0 if within else 0.0
        fit = round(0.6 * budget_fit + 0.3 * theme_fit + 0.1 * headroom, 4)

        recs.append({
            "destination": dest,
            "est_total": f"{est:,}원",
            "affordable_level": lvl,
            "within_budget": within,
            "matched_themes": matched,
            "fit_score": fit,
            "reason": _reason(dest, matched, within, lvl, people, days),
        })

    recs.sort(key=lambda r: (-(1 if r["within_budget"] else 0), -r["fit_score"], r["destination"]))
    top = recs[:limit]

    return {
        "agent": "travel_recommender_agent",
        "data_source": "rule_based",
        "summary": f"예산 {budget_total:,}원 · {people}명 · {days}일 기준 추천 {len(top)}곳",
        "recommendations": top,
        "debug_info": {"budget_total": budget_total, "people": people, "days": days, "themes": themes},
    }
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `pytest tests/test_recommender.py -v`
Expected: PASS (4 passed)

- [ ] **Step 6: Commit**

```bash
git add agents/travel_recommender_agent/ tests/test_recommender.py
git commit -m "feat: add travel_recommender_agent (budget/theme destination ranking)"
```

---

### Task 4: `POST /recommend` 엔드포인트

**Files:**
- Modify: `main.py`
- Test: `tests/test_recommend_endpoint.py`

- [ ] **Step 1: 실패하는 테스트 작성**

Create `tests/test_recommend_endpoint.py`:
```python
from fastapi.testclient import TestClient
import main

client = TestClient(main.app)


def test_recommend_returns_candidates():
    resp = client.post("/recommend", json={"budget_total": 1500000, "people": 2, "days": 3, "themes": ["healing"]})
    assert resp.status_code == 200
    data = resp.json()
    assert "recommendations" in data
    assert len(data["recommendations"]) <= 5
    if data["recommendations"]:
        r = data["recommendations"][0]
        assert "destination" in r and "est_total" in r and "within_budget" in r
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_recommend_endpoint.py -v`
Expected: FAIL — 404 (엔드포인트 없음)

- [ ] **Step 3: 모델 추가**

In `main.py`, after the line `class TravelPlanUpdateRequest(BaseModel): title: Optional[str] = None; content_json: Optional[dict] = None`, add:
```python
class RecommendRequest(BaseModel):
    budget_total: int
    people: int = 1
    days: int = 3
    themes: list[str] = Field(default_factory=list)
    origin: str | None = None
```

- [ ] **Step 4: 엔드포인트 추가**

In `main.py`, immediately before the line `@app.get("/agent-library")`, add:
```python
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
    return {"input_echo": payload.dict(), **result}
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `pytest tests/test_recommend_endpoint.py -v`
Expected: PASS (1 passed)

- [ ] **Step 6: 전체 테스트 + 컴파일**

Run: `pytest -q && python -m py_compile main.py`
Expected: all passed, no compile error

- [ ] **Step 7: Commit**

```bash
git add main.py tests/test_recommend_endpoint.py
git commit -m "feat: add POST /recommend endpoint"
```

---

### Task 5: 프런트엔드 추천 패널

**Files:**
- Modify: `static/index.html`

- [ ] **Step 1: 추천 입력/결과 섹션 추가**

In `static/index.html`, find the exact line `<section class="archive-section">` and insert the following block **immediately before** it:
```html
      <section class="archive-section" id="recommend-section">
        <p style="font-weight: 900; font-size: 0.7rem; letter-spacing: 0.4em; margin-bottom: 30px;">예산으로 여행 찾기</p>
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(160px, 1fr)); gap:15px; max-width:760px; margin:0 auto 25px;">
          <input id="rec-budget" type="number" placeholder="총 예산(원)" style="padding:14px; border-radius:14px; border:1px solid var(--line);" />
          <input id="rec-people" type="number" placeholder="인원수" min="1" value="2" style="padding:14px; border-radius:14px; border:1px solid var(--line);" />
          <input id="rec-days" type="number" placeholder="여행일수(일)" min="1" value="3" style="padding:14px; border-radius:14px; border:1px solid var(--line);" />
        </div>
        <div id="rec-themes" style="display:flex; flex-wrap:wrap; gap:10px; justify-content:center; margin-bottom:25px;">
          <label><input type="checkbox" name="rec-theme" value="healing" /> 힐링</label>
          <label><input type="checkbox" name="rec-theme" value="activity" /> 액티비티</label>
          <label><input type="checkbox" name="rec-theme" value="foodie" /> 미식</label>
          <label><input type="checkbox" name="rec-theme" value="photo" /> 사진</label>
          <label><input type="checkbox" name="rec-theme" value="culture" /> 문화</label>
        </div>
        <div style="text-align:center;"><button id="rec-button" class="nav-btn" style="height:50px; padding:0 35px;">추천받기</button></div>
        <div id="rec-result"></div>
      </section>
```

- [ ] **Step 2: 추천 로직 JS 추가**

In `static/index.html`, find the exact line:
`      document.querySelector("#save-plan-button").addEventListener("click", saveCurrentPlan);`
and insert the following **immediately before** it:
```javascript
      async function runRecommend() {
        const budget = parseInt(document.querySelector("#rec-budget").value) || 0;
        const people = parseInt(document.querySelector("#rec-people").value) || 1;
        const days = parseInt(document.querySelector("#rec-days").value) || 1;
        if (!budget) return alert("총 예산을 입력하세요.");
        const themes = Array.from(document.querySelectorAll('input[name="rec-theme"]:checked')).map(c => c.value);
        const box = document.querySelector("#rec-result");
        box.innerHTML = `<p style="text-align:center; padding:30px;">추천 중...</p>`;
        try {
          const resp = await fetch("/recommend", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ budget_total: budget, people, days, themes }) });
          const data = await resp.json();
          if (!resp.ok) throw new Error(data.detail || "추천 실패");
          renderRecommendations(data.recommendations || [], { people, days, themes });
        } catch (e) { box.innerHTML = `<p style="text-align:center; color:#e53e3e; padding:30px;">오류: ${escapeHtml(e.message)}</p>`; }
      }
      function renderRecommendations(recs, ctx) {
        const box = document.querySelector("#rec-result");
        if (!recs.length) { box.innerHTML = `<p style="text-align:center; padding:30px;">추천 결과가 없습니다.</p>`; return; }
        box.innerHTML = `<div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(300px, 1fr)); gap:20px; margin-top:30px;">${recs.map(r => `
          <div class="timeline-block" style="text-align:left; ${r.within_budget ? "" : "opacity:0.55;"}">
            <strong style="font-size:1.2rem;">${escapeHtml(r.destination)}</strong>
            <p style="margin:8px 0; font-weight:800;">${escapeHtml(r.est_total)} ${r.within_budget ? `· ${escapeHtml(r.affordable_level || "")}` : "· 예산 초과"}</p>
            <p style="font-size:0.85rem; color:var(--muted); margin-bottom:12px;">${escapeHtml(r.reason)}</p>
            <button class="nav-btn" style="height:42px; padding:0 22px;" onclick='exploreRecommendation(${JSON.stringify({ destination: r.destination, days: ctx.days, themes: ctx.themes }).replace(/'/g, "&#39;")})'>이 여정 자세히 보기</button>
          </div>`).join("")}</div>`;
      }
      function exploreRecommendation(sel) {
        document.querySelector("#destination-select").value = sel.destination;
        document.querySelector("#run-button").click();
      }
      document.querySelector("#rec-button").addEventListener("click", runRecommend);
```

- [ ] **Step 3: 서버 띄우고 수동 확인**

Run (background): `python -m uvicorn main:app --host 127.0.0.1 --port 8023`
Then: `curl -s -X POST http://127.0.0.1:8023/recommend -H "Content-Type: application/json" -d "{\"budget_total\":1500000,\"people\":2,\"days\":3,\"themes\":[\"healing\"]}"`
Expected: JSON with `recommendations` 배열. 브라우저 `http://127.0.0.1:8023`에서 "예산으로 여행 찾기" 패널 → 추천받기 동작 확인. 확인 후 서버 종료.

- [ ] **Step 4: Commit**

```bash
git add static/index.html
git commit -m "feat: add budget/theme recommendation panel to UI"
```

---

### Task 6: smoke 테스트 보강 + 최종 검증

**Files:**
- Modify: `scripts/smoke_test.py` (선택)

- [ ] **Step 1: smoke에 /recommend 추가 (파일이 요청 기반이면 케이스 추가)**

`scripts/smoke_test.py`를 열어 기존 케이스 패턴을 따라 `POST /recommend`(body `{"budget_total":1500000,"people":2,"days":3,"themes":["healing"]}`) 호출 후 응답에 `recommendations` 키가 있는지 확인하는 케이스를 추가한다. (기존 케이스 구조를 그대로 모방; 새로운 헬퍼 도입 금지)

- [ ] **Step 2: 전체 테스트 통과 확인**

Run: `pytest -q`
Expected: all passed

- [ ] **Step 3: 앱 임포트/컴파일 확인**

Run: `python -m py_compile main.py budget_model.py agents/travel_recommender_agent/main.py agents/travel_budget_agent/main.py`
Expected: no error

- [ ] **Step 4: Commit**

```bash
git add scripts/smoke_test.py
git commit -m "test: add /recommend smoke case"
```

---

## Self-Review 결과
- 스펙 커버리지: 입력(예산/인원/일수/테마) → Task 4/5, 추천 N=5 → Task 3(limit 기본 5), 객실=ceil(people/2) → Task 1, 자동 수준 결정 → Task 3 `_affordable`, 공용 예산모델 → Task 1·2, 점수화 → Task 3, 엔드포인트 → Task 4, UI → Task 5, 테스트 → 각 Task. 누락 없음.
- 플레이스홀더 없음(모든 코드 전체 기재).
- 타입/시그니처 일관: `estimate_budget(...)` 반환 `{"estimated_budget":{...정수}, "total":정수}`을 budget 에이전트·recommender 모두 동일 사용. `recommendations[]` 필드명 UI와 일치.
