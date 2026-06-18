# 여행 방식 워크플로우 Phase 1 구현 계획 (데이터 모델 + 조건→에이전트 반영)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 여행 형태·이동수단·페이스·확장 테마를 워크플로우 입력으로 받아 각 에이전트(예산/일정/숙박/맛집/관광/행사)가 그 조건을 정확히 반영하도록 만든다.

**Architecture:** `WorkflowRequest`에 `travel_format`/`transport_mode`/`pace`를 추가해 `input_data`로 주입한다. `budget_model`은 이동수단·미식 테마를 비용에 반영하고, 각 에이전트는 input_data의 조건을 읽어 출력에 반영한다. 모든 신규 필드는 기본값이 있어 기존 호출과 하위호환된다. 검증 게이트(Phase 2)와 UI(Phase 3)는 별도 계획.

**Tech Stack:** FastAPI, Pydantic v2, pytest, 동적 로드 에이전트(`agents/*/main.py`).

**정규값 정의 (전 Phase 공통):**
- `travel_format` ∈ {`자유여행`(기본), `당일치기`, `캠핑/차박`, `기차여행`, `패키지`}
- `transport_mode` ∈ {`자가용`, `기차/KTX`, `항공`, `대중교통`, `렌터카`} 또는 `None`(기본)
- `pace` ∈ {`빡빡`, `보통`(기본), `여유`}
- `themes` 값: 기존 `healing` `activity` `foodie` `photo` `culture` + 신규 `nature` `wellness` `festival` `family_kids` `gourmet`

---

### Task 1: WorkflowRequest 신규 필드 + input_data 주입 + 당일치기/가족키즈 보정

**Files:**
- Modify: `main.py` (`WorkflowRequest` 클래스, `run_workflow` 함수)
- Test: `tests/test_workflow_axes.py` (Create)

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_workflow_axes.py`:
```python
from fastapi.testclient import TestClient
import main

client = TestClient(main.app)

BASE = {
    "user_request": "", "destination": "속초", "origin": "서울",
    "days": 3, "budget_level": "medium", "requested_features": ["budget", "schedule", "lodging"],
    "additional_conditions": {"themes": []},
}

def _run(**over):
    payload = {**BASE, **over}
    r = client.post("/run-workflow", json=payload)
    assert r.status_code == 200, r.text
    return r.json()

def test_new_axes_injected_into_input_data():
    d = _run(travel_format="기차여행", transport_mode="기차/KTX", pace="여유")
    assert d["input_data"]["travel_format"] == "기차여행"
    assert d["input_data"]["transport_mode"] == "기차/KTX"
    assert d["input_data"]["pace"] == "여유"

def test_day_trip_forces_one_day():
    d = _run(travel_format="당일치기", days=5)
    assert d["input_data"]["days"] == 1

def test_family_kids_theme_adds_family_companion():
    d = _run(additional_conditions={"themes": ["family_kids"], "companions": []})
    assert "family" in d["input_data"]["companions"]
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_workflow_axes.py -q`
Expected: FAIL (travel_format 등 KeyError / days=5 / family 없음)

- [ ] **Step 3: 구현 — WorkflowRequest 필드 추가**

`main.py`의 `class WorkflowRequest` 안 `days: int | None = None` 다음 줄에 추가:
```python
    travel_format: str = "자유여행"
    transport_mode: str | None = None
    pace: str = "보통"
```

- [ ] **Step 4: 구현 — run_workflow 주입 + 보정**

`run_workflow`에서 `days = payload.days or 3` 다음에 추가:
```python
    if payload.travel_format == "당일치기":
        days = 1
```
그리고 `input_data = { ... }` 딕셔너리에 `"duration_days": days,` 다음에 키 3개 추가:
```python
        "travel_format": payload.travel_format, "transport_mode": payload.transport_mode, "pace": payload.pace,
```
`input_data` 정의 블록 바로 다음에 가족키즈 보정 추가:
```python
    if "family_kids" in (input_data.get("themes") or []):
        _comps = list(input_data.get("companions") or [])
        if "family" not in _comps:
            _comps.append("family")
        input_data["companions"] = _comps
```

- [ ] **Step 5: 통과 확인**

Run: `python -m pytest tests/test_workflow_axes.py -q`
Expected: PASS (3개)

- [ ] **Step 6: 커밋**

```bash
git add main.py tests/test_workflow_axes.py
git commit -m "feat(workflow): add travel_format/transport_mode/pace axes + day-trip & family-kids handling"
```

---

### Task 2: budget_model 이동수단·미식 반영 + budget 에이전트 전달

**Files:**
- Modify: `budget_model.py` (`estimate_budget`, `_intercity_transport`)
- Modify: `agents/travel_budget_agent/main.py` (`run`)
- Test: `tests/test_budget_model.py` (확장)

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_budget_model.py` 끝에 추가:
```python
def test_transport_mode_changes_cost():
    base = estimate_budget("서울", "대전", days=3, level="medium", people=1)["estimated_budget"]["transportation"]
    air = estimate_budget("서울", "대전", days=3, level="medium", people=1, transport_mode="항공")["estimated_budget"]["transportation"]
    transit = estimate_budget("서울", "대전", days=3, level="medium", people=1, transport_mode="대중교통")["estimated_budget"]["transportation"]
    assert air > base > transit

def test_transport_mode_none_is_legacy():
    a = estimate_budget("서울", "대전", days=3, level="medium", people=1)["estimated_budget"]["transportation"]
    b = estimate_budget("서울", "대전", days=3, level="medium", people=1, transport_mode=None)["estimated_budget"]["transportation"]
    assert a == b

def test_gourmet_theme_raises_food():
    plain = estimate_budget("서울", "대전", days=3, level="medium", people=1)["estimated_budget"]["food"]
    gourmet = estimate_budget("서울", "대전", days=3, level="medium", people=1, themes=["gourmet"])["estimated_budget"]["food"]
    assert gourmet > plain
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_budget_model.py -q`
Expected: FAIL (transport_mode 인자 미지원 / food 동일)

- [ ] **Step 3: 구현 — budget_model**

`budget_model.py` 상단 상수 영역(`SEOUL_BUSAN_KM = 325.0` 다음)에 추가:
```python
TRANSPORT_MODE_COEFF = {"대중교통": 0.7, "기차/KTX": 1.0, "렌터카": 1.1, "자가용": 0.8, "항공": 1.8}
```
`_intercity_transport(origin, destination, level)` 시그니처를 다음으로 변경:
```python
def _intercity_transport(origin, destination, level, transport_mode=None):
```
함수 안 `if "제주" in (origin, destination): return JEJU_AIR_DEFAULT[level]` 는 그대로 두고(제주는 항공 고정), 마지막 `return _round_krw(max(raw, TRANSPORT_FLOOR[level]))` 를 다음으로 교체:
```python
    coeff = TRANSPORT_MODE_COEFF.get(transport_mode, 1.0)
    return _round_krw(max(raw * coeff, TRANSPORT_FLOOR[level]))
```
또한 명시 테이블 분기도 수단을 반영하도록, `if explicit: return explicit[level]` 를 다음으로 교체:
```python
    if explicit:
        return _round_krw(explicit[level] * TRANSPORT_MODE_COEFF.get(transport_mode, 1.0))
```
`estimate_budget` 시그니처에 `transport_mode=None` 추가:
```python
def estimate_budget(origin, destination, days, level, people=1, themes=None, companions=None, priority=None, transport_mode=None):
```
`estimate_budget` 안 `if "activity" in themes: unit["tour_event_per_day"] *= 1.5` 다음에 추가:
```python
    if "gourmet" in themes:
        unit["meal_per_count"] *= 1.3
```
그리고 `long_dist = _intercity_transport(origin, destination, level)` 를 다음으로 교체:
```python
    long_dist = _intercity_transport(origin, destination, level, transport_mode)
```

- [ ] **Step 4: 구현 — budget 에이전트 전달**

`agents/travel_budget_agent/main.py`의 `run`에서 `people = safe_input.get("people", 1)` 다음에 추가:
```python
    transport_mode = safe_input.get("transport_mode")
```
`estimate_budget(...)` 호출에 `transport_mode=transport_mode` 인자를 추가:
```python
    result = estimate_budget(origin, destination, days, budget_level,
                             people=people, themes=themes, companions=companions, priority=priority,
                             transport_mode=transport_mode)
```

- [ ] **Step 5: 통과 확인**

Run: `python -m pytest tests/test_budget_model.py tests/test_recommender.py -q`
Expected: PASS (기존 + 신규 3개. recommender는 transport_mode 미전달이라 영향 없음)

- [ ] **Step 6: 커밋**

```bash
git add budget_model.py agents/travel_budget_agent/main.py tests/test_budget_model.py
git commit -m "feat(budget): reflect transport_mode and gourmet theme in cost"
```

---

### Task 3: 일정 에이전트 페이스 → 하루 일정 밀도

**Files:**
- Modify: `agents/travel_schedule_agent/main.py` (`run`)
- Test: `tests/test_schedule_pace.py` (Create)

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_schedule_pace.py`:
```python
import importlib.util
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def _load():
    spec = importlib.util.spec_from_file_location("schedule_ut", ROOT / "agents" / "travel_schedule_agent" / "main.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def _blocks_day2(pace):
    sch = _load()
    res = sch.run({"destination": "속초", "days": 2, "pace": pace, "themes": []})
    return len(res["daily_itinerary"][1]["time_blocks"])

def test_packed_has_more_blocks_than_relaxed():
    assert _blocks_day2("빡빡") > _blocks_day2("여유")

def test_normal_is_default_three():
    assert _blocks_day2("보통") == 3
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_schedule_pace.py -q`
Expected: FAIL (현재 항상 3블록 → 빡빡==여유)

- [ ] **Step 3: 구현**

`agents/travel_schedule_agent/main.py`의 `run`에서 `priority = safe_input.get("priority", "")` 다음에 추가:
```python
    pace = safe_input.get("pace", "보통")
    blocks_per_day = {"빡빡": 4, "보통": 3, "여유": 2}.get(pace, 3)
```
`for d in range(1, days + 1):` 루프 안에서, 기존 블록 생성 뒤에 저녁 블록을 페이스에 따라 덧붙이고 여유는 줄이도록 루프 본문을 다음으로 교체:
```python
        blocks = []
        if d == 1:
            blocks.append(_block("오전", "transport", f"{origin}에서 출발", f"{destination} 주요 지역으로 이동합니다."))
            blocks.append(_block("점심", "food", _pick(food, 0, "로컬 맛집"), "도착 후 첫 식사입니다."))
            blocks.append(_block("오후", "tour", _pick(tour, 0, "핵심 명소"), "가장 가보고 싶었던 장소를 방문합니다."))
        else:
            blocks.append(_block("오전", "tour", _pick(tour, d, "오전 산책/관광"), "여유로운 오전 일정을 시작합니다."))
            blocks.append(_block("점심", "food", _pick(food, d, "추천 식당"), "근처 맛집에서 점심을 해결합니다."))
            blocks.append(_block("오후", "tour", _pick(tour, d+1, "테마 관광"), f"{', '.join(themes)} 테마에 맞춘 일정을 즐깁니다."))
        # 페이스 반영: 여유=오후 일정 축소(2블록), 빡빡=저녁 일정 추가(4블록)
        if blocks_per_day <= 2 and len(blocks) > 2:
            blocks = blocks[:2]
        elif blocks_per_day >= 4:
            blocks.append(_block("저녁", "food", _pick(food, d+2, "저녁 맛집"), "하루를 마무리하는 저녁 일정입니다."))
```
그리고 `debug_info`에 `"pace": pace` 를 추가.

- [ ] **Step 4: 통과 확인**

Run: `python -m pytest tests/test_schedule_pace.py -q`
Expected: PASS (2개)

- [ ] **Step 5: 커밋**

```bash
git add agents/travel_schedule_agent/main.py tests/test_schedule_pace.py
git commit -m "feat(schedule): pace controls daily itinerary density"
```

---

### Task 4: 숙박 에이전트 캠핑/차박 형태 반영

**Files:**
- Modify: `agents/travel_lodging_agent/main.py` (`run`)
- Test: `tests/test_lodging_format.py` (Create)

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_lodging_format.py`:
```python
import importlib.util
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def _load():
    spec = importlib.util.spec_from_file_location("lodging_ut", ROOT / "agents" / "travel_lodging_agent" / "main.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def test_camping_format_returns_campsite():
    res = _load().run({"destination": "속초", "days": 2, "travel_format": "캠핑/차박"})
    titles = " ".join(i["name"] for i in res["lodging_items"])
    cats = " ".join(i["category"] for i in res["lodging_items"])
    assert "캠핑" in titles or "캠핑" in cats or "차박" in titles

def test_default_format_returns_hotel():
    res = _load().run({"destination": "속초", "days": 2})
    cats = " ".join(i["category"] for i in res["lodging_items"])
    assert "호텔" in cats
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_lodging_format.py -q`
Expected: FAIL (캠핑 항목 없음)

- [ ] **Step 3: 구현**

`agents/travel_lodging_agent/main.py`의 `run`에서 `priority = input_data.get("priority", "")` 다음에 추가:
```python
    travel_format = input_data.get("travel_format", "자유여행")
```
`lodging_items = [...]` 정의 직전에 캠핑 분기 추가:
```python
    if travel_format == "캠핑/차박":
        lodging_items = [
            {"name": f"{destination} 오토캠핑장", "address": f"{destination} 인근 캠핑장", "category": "캠핑장",
             "reason": "차박/캠핑에 적합한 사이트입니다."},
            {"name": f"{destination} 글램핑 사이트", "address": f"{destination} 자연 인근", "category": "글램핑",
             "reason": "장비 없이 즐기는 캠핑 옵션입니다."},
        ]
        return {
            "agent": "travel_lodging_agent", "data_source": "mock_plus_conditions",
            "destination": destination, "days": days, "lodging_items": lodging_items,
            "recommendations": ["캠핑/차박 형태에 맞춰 캠핑장·글램핑 위주로 구성했습니다."],
            "summary": f"{destination} {days}일 캠핑/차박 숙박 추천입니다.",
            "debug_info": {"companions": companions, "themes": themes, "priority": priority, "travel_format": travel_format},
        }
```

- [ ] **Step 4: 통과 확인**

Run: `python -m pytest tests/test_lodging_format.py -q`
Expected: PASS (2개)

- [ ] **Step 5: 커밋**

```bash
git add agents/travel_lodging_agent/main.py tests/test_lodging_format.py
git commit -m "feat(lodging): camping/car-camping format returns campsites"
```

---

### Task 5: 신규 테마 키워드 매핑 (관광·맛집·행사)

**Files:**
- Modify: `agents/travel_tour_agent/main.py` (`_get_trip_context`의 `theme_keywords`)
- Modify: `agents/travel_food_agent/main.py` (`run` — gourmet/nature 요약 보강)
- Modify: `agents/travel_event_agent/main.py` (`run`의 `theme_keywords`)
- Test: `tests/test_theme_keywords.py` (Create)

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_theme_keywords.py`:
```python
import importlib.util
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def _load(agent):
    spec = importlib.util.spec_from_file_location(f"{agent}_ut", ROOT / "agents" / agent / "main.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def test_tour_context_maps_new_themes():
    tour = _load("travel_tour_agent")
    _safe, _loc, _per, _cat, keyword = tour._get_trip_context({"destination": "속초", "themes": ["nature", "wellness"]})
    assert "자연" in keyword or "수목원" in keyword
    assert "온천" in keyword or "스파" in keyword

def test_event_maps_festival_theme():
    ev = _load("travel_event_agent")
    res = ev.run({"destination": "속초", "themes": ["festival"]})
    assert res["event_items"]

def test_food_gourmet_summary():
    food = _load("travel_food_agent")
    res = food.run({"destination": "속초", "themes": ["gourmet"]})
    assert "미슐랭" in res["summary"] or "파인다이닝" in res["summary"] or "베이커리" in res["summary"]
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_theme_keywords.py -q`
Expected: FAIL (nature/wellness 키워드 없음, gourmet 요약 없음)

- [ ] **Step 3: 구현 — tour 에이전트**

`agents/travel_tour_agent/main.py`의 `_get_trip_context` 안 `theme_keywords` 딕셔너리에 항목 추가:
```python
        "nature": "자연 수목원 숲 해변",
        "wellness": "온천 스파 휴양",
        "festival": "축제 거리 행사",
        "family_kids": "체험 동물원 테마파크",
        "gourmet": "맛집 베이커리 미식",
```

- [ ] **Step 4: 구현 — event 에이전트**

`agents/travel_event_agent/main.py`의 `theme_keywords` 딕셔너리에 추가:
```python
        "festival": "축제 페스티벌 불꽃축제",
        "culture": "전통 공연 역사",
```
그리고 `summary` 보강부에 추가:
```python
    if "festival" in themes: summary += "지역 축제·페스티벌 일정을 우선 반영했습니다."
```

- [ ] **Step 5: 구현 — food 에이전트**

`agents/travel_food_agent/main.py`의 `run`에서 `summary` 보강부(`if priority == "cost": ...` 다음)에 추가:
```python
    if "gourmet" in themes:
        summary += "베이커리·파인다이닝·미슐랭급 맛집을 우선 선별했습니다."
```

- [ ] **Step 6: 통과 확인**

Run: `python -m pytest tests/test_theme_keywords.py -q`
Expected: PASS (3개)

- [ ] **Step 7: 커밋**

```bash
git add agents/travel_tour_agent/main.py agents/travel_event_agent/main.py agents/travel_food_agent/main.py tests/test_theme_keywords.py
git commit -m "feat(agents): map new themes (nature/wellness/festival/family_kids/gourmet) to keywords"
```

---

### Task 6: 전체 회귀 확인

- [ ] **Step 1: 전체 단위 + smoke**

Run:
```bash
python -m pytest tests/ -q
python -m uvicorn main:app --host 127.0.0.1 --port 8013 &  # 이미 떠있으면 생략
BASE_URL=http://localhost:8013 python scripts/smoke_test.py
```
Expected: 단위 전부 PASS, smoke 15/15 PASS (신규 필드 기본값 하위호환).

- [ ] **Step 2: 하위호환 수동 확인**

Run: `curl -s -X POST http://localhost:8013/run-workflow -H "Content-Type: application/json" -d '{"user_request":"","destination":"부산","days":3,"requested_features":["budget"]}'`
Expected: 200, 신규 필드 없이도 정상 응답.

---

## 다음 단계 (별도 계획)
- **Phase 2:** 검증 게이트 — 각 `agent_results[i]`에 `verification`(`verified`/`estimated`) + 정합성 검사(`validators/travel_validator.py`), 응답 필드.
- **Phase 3:** UI — 프리셋 카드 + 세부 패널(형태·이동수단·테마10·페이스) + 검증 배지/토글, `runWorkflow` payload 확장, 브라우저 E2E.
- **보류:** 교통 에이전트 내부 수단 우선/제한(예산은 이미 수단 반영), 패키지 묶음예산.
