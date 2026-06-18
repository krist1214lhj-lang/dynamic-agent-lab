# UI 시각 통일 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 폼 영역 외형(반경·선택표시)을 통일하고 프리셋 이모지를 제거해 "중구난방·정신 사나움"을 해소한다. 구조·순서·JS·기능 불변.

**Architecture:** `static/index.html`의 `<style>` 토큰화 + 선택상태 CSS 교체 + `renderPresets` 이모지 제거. DOM 순서·id·핸들러는 건드리지 않아 기존 7개 계약 테스트와 모든 기능이 그대로 통과한다.

**Tech Stack:** 정적 HTML/CSS/Vanilla JS, pytest(HTML 계약), gstack(브라우저 E2E).

스펙: `docs/superpowers/specs/2026-06-18-ui-visual-unification-design.md`

---

### Task 1: 계약 테스트(가드) 추가

**Files:** Modify `tests/test_ui_contract.py`

- [ ] **Step 1: 실패 테스트 작성** — 파일 끝에 추가:
```python
def test_radius_token_defined():
    assert "--radius:" in HTML

def test_calm_selection_color_present():
    assert "#f1f5f9" in HTML

def test_no_preset_emoji():
    for emoji in ["🍞", "🏕️", "♨️", "📸", "🎏", "🚄", "⚙️"]:
        assert emoji not in HTML, f"preset emoji still present: {emoji}"
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_ui_contract.py -q` → FAIL (--radius/#f1f5f9 없음, 이모지 존재).

---

### Task 2: 반경 토큰 + 차분한 선택 + 흐림 제거 (CSS)

**Files:** Modify `static/index.html` `<style>`

- [ ] **Step 1: `--radius` 토큰 추가** — `:root {` 다음 줄에 `--radius: 16px;` 추가(첫 속성 줄로).

- [ ] **Step 2: 폼 입력/칩/프리셋 반경 통일**
  - `.search-field input[type="date"], .search-field select`의 `border-radius: 18px;` → `border-radius: var(--radius);`
  - `.auth-form input`의 `border-radius: 20px;` → `border-radius: var(--radius);`
  - `textarea#user-request`의 `border-radius: 25px;` → `border-radius: var(--radius);`
  - `.checkbox-grid label`의 `border-radius: 999px;` → `border-radius: var(--radius);`
  - `.preset-card`의 `border-radius: 20px;` → `border-radius: var(--radius);`
  - `.tab-btn`의 `border-radius: 999px;` → `border-radius: var(--radius);`

- [ ] **Step 3: 차분한 선택 표시**
  - `.checkbox-grid label:has(input:checked) { background: var(--accent); color: #fff; border-color: var(--accent); }` → `.checkbox-grid label:has(input:checked) { background: #f1f5f9; color: var(--text); border-color: var(--accent); font-weight: 600; }`
  - 그 줄 다음에 추가: `.checkbox-grid label:has(input:checked)::before { content: "✓ "; font-weight: 900; }`
  - `.preset-card.active { background: var(--accent); color: #fff; border-color: var(--accent); }` → `.preset-card.active { background: #f1f5f9; color: var(--text); border-color: var(--accent); }`
  - `.tab-btn.active { background: var(--accent); color: #fff; border-color: var(--accent); }` → `.tab-btn.active { background: #f1f5f9; color: var(--accent); border-color: var(--accent); }`

- [ ] **Step 4: 흐림 효과 제거**
  - `.archive-section`의 `opacity: 0.4;` → `opacity: 1;`
  - `.archive-section:hover { opacity: 1; }` 줄 삭제.

- [ ] **Step 5: rec 입력칸 반경 통일** — 3개 입력칸(`rec-budget`/`rec-people`/`rec-days`)의 `padding:14px; border-radius:14px;` → `padding:14px 18px; border-radius:16px;` (replace_all).

---

### Task 3: 프리셋 이모지 제거 (JS + CSS 정리)

**Files:** Modify `static/index.html`

- [ ] **Step 1: 렌더 템플릿에서 이모지 span 제거**
  - `grid.innerHTML = PRESETS.map(p => \`<div class="preset-card" data-preset-id="${p.id}"><span class="preset-emoji">${p.emoji}</span><span class="preset-label">${escapeHtml(p.label)}</span></div>\`).join("");` → `<span class="preset-emoji">…</span>` 부분 제거.

- [ ] **Step 2: PRESETS 배열에서 `emoji:` 필드 제거** (7개 항목 각각 `emoji:"…",` 토큰 제거).

- [ ] **Step 3: `.preset-emoji` CSS 규칙 삭제.**

---

### Task 4: 검증 + 커밋

- [ ] **Step 1: 계약 테스트 green** — Run: `python -m pytest tests/test_ui_contract.py -q` → PASS(10).
- [ ] **Step 2: 전체 단위** — Run: `python -m pytest tests/ -q` → 전부 PASS.
- [ ] **Step 3: 브라우저 E2E** — 서버 기동 후 gstack으로: 콘솔 에러 0, 프리셋 "캠핑 자연" 클릭 → 테마 다중선택 상태 스크린샷(차분한 연회색+✓ 확인), 워크플로우 실행 정상 렌더. 이모지 없음 확인.
- [ ] **Step 4: 커밋**
```bash
git add static/index.html tests/test_ui_contract.py
git commit -m "refactor(ui): unify radii, calm multi-select state, drop preset emojis"
```
