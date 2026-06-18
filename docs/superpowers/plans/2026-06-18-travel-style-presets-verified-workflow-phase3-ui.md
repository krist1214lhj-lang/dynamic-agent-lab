# 여행 방식 워크플로우 Phase 3 (UI: 프리셋 + 세부 패널) 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Phase 1에서 백엔드에 추가된 축(여행 형태·이동수단·페이스·테마 10종)을 프런트엔드 UI에 노출하고, "여행 방식 프리셋" 카드로 빠르게 채울 수 있게 한다.

**Architecture:** `static/index.html`(인라인 CSS/JS, 빌드 단계 없음) 단일 파일을 수정한다. 메인 워크플로우 폼에 형태/이동수단/페이스 셀렉트와 확장된 테마 체크박스를 추가하고, `runWorkflow`의 payload에 신규 필드를 더한다. 상단에 프리셋 카드 그리드를 추가해 클릭 시 패널 값을 자동 채운다. 모든 신규 필드는 Phase 1 백엔드가 이미 기본값으로 받으므로 하위호환된다.

**Tech Stack:** 정적 HTML/CSS/Vanilla JS, FastAPI(`/run-workflow`), pytest(HTML 계약 테스트), gstack(브라우저 E2E).

**범위(이번 Phase):** 프리셋 카드 + 세부 패널(형태·이동수단·테마10·페이스) + payload 확장.

**비범위(이번 Phase 제외):**
- 검증 배지(`verification`)/"검증된 것만 보기" 토글 → Phase 2 백엔드 선행 후 별도 진행.
- `가족·키즈` 테마 선택 시 동행 자동 동기화 → 백엔드(`main.py`)가 이미 `family_kids` 테마에 `family` 동행을 주입하므로 UI 중복 구현하지 않음.
- "예산으로 여행 찾기"(`#rec-themes`) 패널의 테마는 그대로 5종 유지(별개 기능, 변경 불필요).

**테마 값 매핑(백엔드 값 = 정규값):**
`healing`(힐링) · `activity`(액티비티) · `foodie`(맛집탐방) · `photo`(사진) · `culture`(문화) · `nature`(자연/풍경) · `wellness`(휴양/온천·스파) · `festival`(축제/이벤트) · `family_kids`(가족·키즈) · `gourmet`(미식 심화)

---

### Task 1: 메인 테마 탭을 5종 → 10종으로 확장

**Files:**
- Create: `tests/test_ui_contract.py`
- Modify: `static/index.html` (`#tab-theme` 블록)

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_ui_contract.py`:
```python
from pathlib import Path

HTML = (Path(__file__).resolve().parents[1] / "static" / "index.html").read_text(encoding="utf-8")

TEN_THEMES = ["healing", "activity", "foodie", "photo", "culture",
              "nature", "wellness", "festival", "family_kids", "gourmet"]

def test_theme_tab_has_ten_themes():
    for val in TEN_THEMES:
        assert f'name="theme" value="{val}"' in HTML, f"missing theme: {val}"
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_ui_contract.py -q`
Expected: FAIL (nature/wellness/festival/family_kids/gourmet 없음)

- [ ] **Step 3: 구현 — 테마 5종 추가**

`static/index.html`의 `#tab-theme` 안에서 다음 줄
```html
              <label><input type="checkbox" name="theme" value="culture" />역사/문화</label>
```
바로 다음에 5줄을 추가:
```html
              <label><input type="checkbox" name="theme" value="nature" />자연/풍경</label>
              <label><input type="checkbox" name="theme" value="wellness" />휴양/온천·스파</label>
              <label><input type="checkbox" name="theme" value="festival" />축제/이벤트</label>
              <label><input type="checkbox" name="theme" value="family_kids" />가족·키즈</label>
              <label><input type="checkbox" name="theme" value="gourmet" />미식 심화</label>
```

- [ ] **Step 4: 통과 확인**

Run: `python -m pytest tests/test_ui_contract.py -q`
Expected: PASS (1개)

- [ ] **Step 5: 커밋**

```bash
git add tests/test_ui_contract.py static/index.html
git commit -m "feat(ui): expand theme tab to 10 themes (nature/wellness/festival/family_kids/gourmet)"
```

---

### Task 2: 형태·이동수단·페이스 셀렉트 추가 + runWorkflow payload 확장

**Files:**
- Modify: `static/index.html` (`.search-bar-row` 다음에 행 추가, `runWorkflow` payload)
- Modify: `tests/test_ui_contract.py` (테스트 추가)

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_ui_contract.py` 끝에 추가:
```python
def test_axis_controls_present():
    for el_id in ["travel-format-select", "transport-mode-select", "pace-select"]:
        assert f'id="{el_id}"' in HTML, f"missing control: {el_id}"

def test_travel_format_options():
    for v in ["자유여행", "당일치기", "캠핑/차박", "기차여행", "패키지"]:
        assert f'value="{v}"' in HTML, f"missing travel_format option: {v}"

def test_transport_mode_options():
    for v in ["자가용", "기차/KTX", "항공", "대중교통", "렌터카"]:
        assert f'value="{v}"' in HTML, f"missing transport_mode option: {v}"

def test_pace_options():
    for v in ["빡빡", "보통", "여유"]:
        assert f'value="{v}"' in HTML, f"missing pace option: {v}"

def test_runworkflow_payload_includes_axes():
    assert "travel_format:" in HTML
    assert "transport_mode:" in HTML
    assert "pace:" in HTML
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_ui_contract.py -q`
Expected: FAIL (셀렉트/옵션/payload 키 없음)

- [ ] **Step 3: 구현 — 셀렉트 행 추가**

`static/index.html`의 `.search-bar-row`를 닫는 부분, 즉
```html
          <button id="run-button" type="button">여정 그리기</button>
        </div>
```
바로 다음에 새 블록을 추가:
```html
        <div class="travel-style-row" style="display:grid; grid-template-columns:repeat(3, 1fr); gap:12px; margin-top:15px;">
          <label class="search-field">여행 형태
            <select id="travel-format-select">
              <option value="자유여행" selected>자유여행</option>
              <option value="당일치기">당일치기</option>
              <option value="캠핑/차박">캠핑/차박</option>
              <option value="기차여행">기차여행</option>
              <option value="패키지">패키지</option>
            </select>
          </label>
          <label class="search-field">이동수단
            <select id="transport-mode-select">
              <option value="" selected>상관없음</option>
              <option value="자가용">자가용</option>
              <option value="기차/KTX">기차/KTX</option>
              <option value="항공">항공</option>
              <option value="대중교통">대중교통</option>
              <option value="렌터카">렌터카</option>
            </select>
          </label>
          <label class="search-field">여행 페이스
            <select id="pace-select">
              <option value="빡빡">빡빡하게</option>
              <option value="보통" selected>보통</option>
              <option value="여유">여유롭게</option>
            </select>
          </label>
        </div>
```

- [ ] **Step 4: 구현 — runWorkflow payload 확장**

`static/index.html`의 `runWorkflow` 함수 payload에서
```javascript
          budget_level: document.querySelector("#budget-select").value,
```
바로 다음에 3줄 추가:
```javascript
          travel_format: document.querySelector("#travel-format-select").value,
          transport_mode: document.querySelector("#transport-mode-select").value || null,
          pace: document.querySelector("#pace-select").value,
```

- [ ] **Step 5: 통과 확인**

Run: `python -m pytest tests/test_ui_contract.py -q`
Expected: PASS (6개)

- [ ] **Step 6: 커밋**

```bash
git add static/index.html tests/test_ui_contract.py
git commit -m "feat(ui): add travel_format/transport_mode/pace controls + extend runWorkflow payload"
```

---

### Task 3: 여행 방식 프리셋 카드 추가

**Files:**
- Modify: `static/index.html` (CSS 추가, 프리셋 섹션 추가, JS 추가, DOMContentLoaded 초기화)
- Modify: `tests/test_ui_contract.py` (테스트 추가)

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_ui_contract.py` 끝에 추가:
```python
def test_presets_defined():
    for label in ["미식 자유여행", "캠핑 자연", "가족 휴양", "인생샷 도시", "축제·이벤트", "기차 여유", "직접 설정"]:
        assert label in HTML, f"missing preset: {label}"
    assert 'id="preset-grid"' in HTML
    assert "function applyPreset" in HTML
    assert "function renderPresets" in HTML
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_ui_contract.py -q`
Expected: FAIL (프리셋 라벨/함수 없음)

- [ ] **Step 3: 구현 — CSS 추가**

`static/index.html`의 `<style>` 안, 마지막 규칙
```css
      .customized-label { font-size: 0.6rem; vertical-align: middle; margin-left: 15px; padding: 4px 12px; background: #000; color: #fff; border-radius: 99px; font-weight: 700; letter-spacing: 0.1em; }
```
바로 다음에 추가:
```css
      .preset-grid { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 15px; }
      .preset-card { background: #fff; border: 1px solid var(--line); border-radius: 20px; padding: 16px 22px; cursor: pointer; transition: all 0.3s; display: flex; flex-direction: column; gap: 4px; min-width: 130px; align-items: flex-start; }
      .preset-card:hover { border-color: #000; transform: translateY(-2px); }
      .preset-card.active { background: var(--accent); color: #fff; border-color: var(--accent); }
      .preset-emoji { font-size: 1.6rem; }
      .preset-label { font-weight: 700; font-size: 0.9rem; }
```

- [ ] **Step 4: 구현 — 프리셋 섹션 추가**

`static/index.html`에서 메인 폼 섹션
```html
      <section class="control-panel">
        <div class="search-bar-row">
```
의 바로 앞(즉 `<section class="control-panel">` 직전)에 새 섹션을 추가:
```html
      <section class="control-panel" id="preset-section">
        <p class="search-field">여행 방식 프리셋</p>
        <div class="preset-grid" id="preset-grid"></div>
      </section>
```

- [ ] **Step 5: 구현 — JS 추가 (PRESETS / renderPresets / applyPreset)**

`static/index.html`의 `<script>` 안, `function initTabs() {...}` 한 줄 정의 바로 다음 줄에 추가:
```javascript
      const PRESETS = [
        { id:"foodie-free", emoji:"🍞", label:"미식 자유여행", travel_format:"자유여행", transport_mode:"기차/KTX", themes:["gourmet","foodie"], pace:"여유" },
        { id:"camping-nature", emoji:"🏕️", label:"캠핑 자연", travel_format:"캠핑/차박", transport_mode:"자가용", themes:["nature","activity"], pace:"여유" },
        { id:"family-rest", emoji:"♨️", label:"가족 휴양", travel_format:"자유여행", transport_mode:"자가용", themes:["wellness","family_kids"], pace:"여유" },
        { id:"photo-city", emoji:"📸", label:"인생샷 도시", travel_format:"자유여행", transport_mode:"대중교통", themes:["photo","culture"], pace:"빡빡" },
        { id:"festival", emoji:"🎏", label:"축제·이벤트", travel_format:"자유여행", transport_mode:"기차/KTX", themes:["festival","culture"], pace:"보통" },
        { id:"train-relax", emoji:"🚄", label:"기차 여유", travel_format:"기차여행", transport_mode:"기차/KTX", themes:["healing","nature"], pace:"여유" },
        { id:"custom", emoji:"⚙️", label:"직접 설정", travel_format:"자유여행", transport_mode:"", themes:[], pace:"보통" },
      ];
      function renderPresets() {
        const grid = document.querySelector("#preset-grid");
        grid.innerHTML = PRESETS.map(p => `<div class="preset-card" data-preset-id="${p.id}"><span class="preset-emoji">${p.emoji}</span><span class="preset-label">${escapeHtml(p.label)}</span></div>`).join("");
        grid.querySelectorAll(".preset-card").forEach(el => el.addEventListener("click", () => applyPreset(PRESETS.find(x => x.id === el.dataset.presetId))));
      }
      function applyPreset(p) {
        if (!p) return;
        document.querySelector("#travel-format-select").value = p.travel_format;
        document.querySelector("#transport-mode-select").value = p.transport_mode;
        document.querySelector("#pace-select").value = p.pace;
        document.querySelectorAll('input[name="theme"]').forEach(c => { c.checked = p.themes.includes(c.value); });
        document.querySelector('.tab-btn[data-tab="theme"]').click();
        document.querySelectorAll("#preset-grid .preset-card").forEach(el => el.classList.toggle("active", el.dataset.presetId === p.id));
      }
```

- [ ] **Step 6: 구현 — 초기화 호출**

`static/index.html`의 `DOMContentLoaded` 핸들러에서
```javascript
        updateAuthUI(); initAuthLogic(); initTabs(); initRating(); loadComments(); loadRatings();
```
를 다음으로 교체(끝에 `renderPresets();` 추가):
```javascript
        updateAuthUI(); initAuthLogic(); initTabs(); initRating(); loadComments(); loadRatings(); renderPresets();
```

- [ ] **Step 7: 통과 확인**

Run: `python -m pytest tests/test_ui_contract.py -q`
Expected: PASS (7개)

- [ ] **Step 8: 커밋**

```bash
git add static/index.html tests/test_ui_contract.py
git commit -m "feat(ui): add travel-style preset cards that auto-fill the panel"
```

---

### Task 4: 전체 회귀 + 브라우저 E2E 검증

- [ ] **Step 1: 전체 단위 테스트**

Run: `python -m pytest tests/ -q`
Expected: 전부 PASS (기존 44 + UI 계약 7).

- [ ] **Step 2: 서버 기동 (깨끗한 포트)**

Run:
```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8026 > /tmp/uvicorn_8026.log 2>&1 &
```
8013/8014/8025가 이미 점유 중일 수 있으므로 새 포트(8026)를 쓴다. `curl -s http://127.0.0.1:8026/health`로 `Initialized` 확인.

- [ ] **Step 3: smoke 하위호환**

Run: `BASE_URL=http://localhost:8026 python scripts/smoke_test.py`
Expected: 15/15 PASS (신규 필드 없이도 동작).

- [ ] **Step 4: 브라우저 E2E (gstack)**

`B="$HOME/.claude/skills/gstack/browse/dist/browse"` 로 다음을 수행:
1. `$B goto http://127.0.0.1:8026/` → `$B wait --networkidle`
2. `$B console --errors` → 에러 0 확인
3. 프리셋 클릭: `$B snapshot -i`로 프리셋 카드 @ref 확인 후 "캠핑 자연" 카드 클릭.
4. 패널 자동채움 확인:
   - `$B js "document.querySelector('#travel-format-select').value"` → `캠핑/차박`
   - `$B js "document.querySelector('#transport-mode-select').value"` → `자가용`
   - `$B js "document.querySelector('#pace-select').value"` → `여유`
   - `$B js "Array.from(document.querySelectorAll('input[name=\\"theme\\"]:checked')).map(c=>c.value).join(',')"` → `activity,nature`(순서 무관, nature·activity 포함)
5. 워크플로우 실행: `$B click "#run-button"` → `$B wait ".result-card"`(또는 `$B js "document.querySelectorAll('.result-card').length"` > 0).
6. 결과가 조건 반영했는지 네트워크로 확인: `$B network`에서 `/run-workflow` 응답 또는 `$B js`로 `currentWorkflowResult.input_data.travel_format` 등이 `캠핑/차박`/`자가용`/`여유`인지 확인.
7. `$B screenshot /tmp/phase3_preset_camping.png` 저장 후 Read 도구로 확인(증거).

Expected: 프리셋 클릭→패널 자동채움→여정 렌더, 콘솔 에러 0, input_data에 신규 축 반영.

- [ ] **Step 5: 하위호환 수동 확인**

프리셋을 누르지 않고(기본값 그대로) `여정 그리기` 실행 → 정상 200 및 결과 렌더 확인. (`travel_format=자유여행`, `transport_mode=null`, `pace=보통` 기본 전송)

---

## 다음 단계 (별도 계획)
- **Phase 2:** 검증 게이트(`verification` 상태 + 정합성 검사) 백엔드 → 응답 필드.
- **Phase 3 (잔여):** Phase 2 완료 후 결과 카드 검증 배지 + "검증된 것만 보기" 토글, `가족·키즈` 테마↔동행 UI 동기화(선택).
