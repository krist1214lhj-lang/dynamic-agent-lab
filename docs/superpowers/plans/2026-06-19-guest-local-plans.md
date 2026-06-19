# 비로그인 로컬저장 + 로그인 마이그레이션 (G4) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 비로그인 사용자가 설계 결과를 localStorage에 저장·관리하고, 로그인 시 확인 후 서버로 이전할 수 있게 한다.

**Architecture:** 전부 `static/index.html` 내부 변경. 경량 `LocalPlans` 헬퍼가 localStorage 직렬화를 캡슐화하고, 기존 `saveCurrentPlan`/`renderSavedPlans`가 로그인 여부로 분기. 로그인 성공 직후 `migrateLocalPlans`가 로컬 플랜을 기존 `/api/plans` POST로 업로드. 서버 API 변경 없음.

**Tech Stack:** Vanilla JS(단일 HTML), FastAPI(기존 `/api/plans` 재사용), pytest(문자열 계약 테스트), gstack(브라우저 E2E).

**검증 메모:** 인라인 JS는 pytest 단위테스트가 부적합하므로, 각 태스크는 `tests/test_ui_contract.py`의 **문자열 존재 계약 테스트**로 회귀를 막고, 실제 동작은 Task 5의 gstack E2E로 검증한다. 이는 기존 UI 작업과 동일한 패턴이다.

## File Structure

- Modify: `static/index.html` — `LocalPlans` 헬퍼 추가, `saveCurrentPlan`/`renderSavedPlans` 분기, `planCardHtml`/`renameLocalPlan`/`deleteLocalPlan`/`migrateLocalPlans` 신규, 로그인 핸들러에 마이그레이션 호출.
- Modify: `tests/test_ui_contract.py` — 신규 식별자 계약 테스트 추가.

---

### Task 1: `LocalPlans` 헬퍼

**Files:**
- Modify: `static/index.html` (L330 `let ...` 선언 직후)
- Test: `tests/test_ui_contract.py`

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_ui_contract.py` 끝에 추가:

```python
def test_local_plans_helper_present():
    assert "onesown_local_plans" in HTML
    assert "const LocalPlans" in HTML
    assert "crypto.randomUUID" in HTML
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_ui_contract.py::test_local_plans_helper_present -v`
Expected: FAIL (`assert "onesown_local_plans" in HTML`)

- [ ] **Step 3: 구현** — `static/index.html`에서 아래 줄

```javascript
      let currentUser = null; let authMode = "login"; let currentWorkflowResult = null; let savedPlansExpanded = false;
```

바로 다음 줄에 헬퍼를 삽입:

```javascript
      const LocalPlans = {
        KEY: "onesown_local_plans",
        _read() { try { return JSON.parse(localStorage.getItem(this.KEY) || "[]"); } catch (e) { return []; } },
        _write(arr) { localStorage.setItem(this.KEY, JSON.stringify(arr)); },
        list() { return this._read(); },
        save(plan) {
          const arr = this._read();
          const id = "local-" + ((window.crypto && crypto.randomUUID && crypto.randomUUID()) || (Date.now() + "-" + Math.random().toString(16).slice(2)));
          arr.unshift({ id, title: plan.title, destination: plan.destination, content_json: plan.content_json, created_at: new Date().toISOString() });
          this._write(arr); return id;
        },
        rename(id, title) { const arr = this._read(); const p = arr.find(x => x.id === id); if (p) { p.title = title; this._write(arr); } },
        remove(id) { this._write(this._read().filter(x => x.id !== id)); },
        clear() { localStorage.removeItem(this.KEY); }
      };
```

- [ ] **Step 4: 통과 확인**

Run: `python -m pytest tests/test_ui_contract.py::test_local_plans_helper_present -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add static/index.html tests/test_ui_contract.py
git commit -m "feat(plans): add LocalPlans localStorage helper"
```

---

### Task 2: 비로그인 저장 분기 (`saveCurrentPlan`)

**Files:**
- Modify: `static/index.html` (`saveCurrentPlan`, 현재 L477-482)
- Test: `tests/test_ui_contract.py`

- [ ] **Step 1: 실패 테스트 작성** — 추가:

```python
def test_guest_save_branch_present():
    assert "LocalPlans.save" in HTML
    assert "이 기기에 저장됨" in HTML
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_ui_contract.py::test_guest_save_branch_present -v`
Expected: FAIL (`assert "LocalPlans.save" in HTML`)

- [ ] **Step 3: 구현** — 아래 기존 함수 전체

```javascript
      async function saveCurrentPlan() {
        if (!currentWorkflowResult || !currentUser) return alert("설계 결과가 없거나 로그인 안됨");
        const title = prompt("제목:", `${currentWorkflowResult.input_data.destination} 여행`); if (!title) return;
        const resp = await fetch(`/api/plans`, { method: "POST", headers: authHeaders({ "Content-Type": "application/json" }), body: JSON.stringify({ title, destination: currentWorkflowResult.input_data.destination, content_json: currentWorkflowResult }) });
        if (resp.ok) { alert("저장됨"); renderSavedPlans(); }
      }
```

를 다음으로 교체:

```javascript
      async function saveCurrentPlan() {
        if (!currentWorkflowResult) return alert("설계 결과가 없습니다");
        const title = prompt("제목:", `${currentWorkflowResult.input_data.destination} 여행`); if (!title) return;
        const dest = currentWorkflowResult.input_data.destination;
        if (currentUser) {
          const resp = await fetch(`/api/plans`, { method: "POST", headers: authHeaders({ "Content-Type": "application/json" }), body: JSON.stringify({ title, destination: dest, content_json: currentWorkflowResult }) });
          if (resp.ok) { alert("저장됨"); renderSavedPlans(); }
        } else {
          LocalPlans.save({ title, destination: dest, content_json: currentWorkflowResult });
          alert("이 기기에 저장됨 (로그인하면 계정으로 옮길 수 있어요)"); renderSavedPlans();
        }
      }
```

- [ ] **Step 4: 통과 확인**

Run: `python -m pytest tests/test_ui_contract.py::test_guest_save_branch_present -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add static/index.html tests/test_ui_contract.py
git commit -m "feat(plans): guest save to localStorage when logged out"
```

---

### Task 3: 보관함 렌더 분기 + 로컬 제목수정/삭제

**Files:**
- Modify: `static/index.html` (`renderSavedPlans` 현재 L483-487; 그 뒤에 신규 함수)
- Test: `tests/test_ui_contract.py`

- [ ] **Step 1: 실패 테스트 작성** — 추가:

```python
def test_local_plan_controls_present():
    assert "function planCardHtml" in HTML
    assert "function renameLocalPlan" in HTML
    assert "function deleteLocalPlan" in HTML
    assert "LocalPlans.list()" in HTML
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_ui_contract.py::test_local_plan_controls_present -v`
Expected: FAIL (`assert "function planCardHtml" in HTML`)

- [ ] **Step 3: 구현** — 아래 기존 함수 전체

```javascript
      async function renderSavedPlans() {
        const list = document.querySelector("#saved-plan-list"); if (!savedPlansExpanded || !currentUser) { list.innerHTML = ""; return; }
        const resp = await fetch(`/api/plans`, { headers: authHeaders() }); const plans = await resp.json();
        list.innerHTML = `<div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(320px, 1fr)); gap:25px; margin-top:40px;">${plans.map(p => `<div class="timeline-block" style="text-align:left;"><div style="cursor:pointer;" onclick='loadSavedPlanData(${JSON.stringify(p.content_json).replace(/'/g, "&apos;")})'><p style="font-size:0.75rem; font-weight:900; opacity:0.3;">${new Date(p.created_at).toLocaleDateString()}</p><strong>${escapeHtml(p.title)}</strong></div><div class="plan-controls"><button class="control-btn edit" onclick="renamePlan('${p.id}', '${escapeHtml(p.title).replace(/'/g, "&#39;")}')">수정</button><button class="control-btn delete" onclick="deletePlan('${p.id}')">삭제</button></div></div>`).join("")}</div>`;
      }
```

를 다음으로 교체(분기 + `planCardHtml` 추출 + 로컬 함수 추가):

```javascript
      function planCardHtml(p, isLocal) {
        const dateStr = p.created_at ? new Date(p.created_at).toLocaleDateString() : "";
        const badge = isLocal ? ` <span class="customized-label" style="background:#f1f5f9; color:var(--text);">이 기기</span>` : "";
        const renameCall = isLocal ? `renameLocalPlan('${p.id}', '${escapeHtml(p.title).replace(/'/g, "&#39;")}')` : `renamePlan('${p.id}', '${escapeHtml(p.title).replace(/'/g, "&#39;")}')`;
        const deleteCall = isLocal ? `deleteLocalPlan('${p.id}')` : `deletePlan('${p.id}')`;
        return `<div class="timeline-block" style="text-align:left;"><div style="cursor:pointer;" onclick='loadSavedPlanData(${JSON.stringify(p.content_json).replace(/'/g, "&apos;")})'><p style="font-size:0.75rem; font-weight:900; opacity:0.3;">${dateStr}${badge}</p><strong>${escapeHtml(p.title)}</strong></div><div class="plan-controls"><button class="control-btn edit" onclick="${renameCall}">수정</button><button class="control-btn delete" onclick="${deleteCall}">삭제</button></div></div>`;
      }
      async function renderSavedPlans() {
        const list = document.querySelector("#saved-plan-list"); if (!savedPlansExpanded) { list.innerHTML = ""; return; }
        let plans, isLocal;
        if (currentUser) { const resp = await fetch(`/api/plans`, { headers: authHeaders() }); plans = await resp.json(); isLocal = false; }
        else { plans = LocalPlans.list(); isLocal = true; }
        if (!Array.isArray(plans) || !plans.length) { list.innerHTML = `<p style="text-align:center; color:var(--muted); margin-top:40px;">저장된 여정이 없습니다.</p>`; return; }
        list.innerHTML = `<div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(320px, 1fr)); gap:25px; margin-top:40px;">${plans.map(p => planCardHtml(p, isLocal)).join("")}</div>`;
      }
      function renameLocalPlan(id, currentTitle) {
        const title = prompt("새 제목:", currentTitle); if (title === null || !title.trim()) return;
        LocalPlans.rename(id, title.trim()); renderSavedPlans();
      }
      function deleteLocalPlan(id) {
        if (confirm("삭제?")) { LocalPlans.remove(id); renderSavedPlans(); }
      }
```

- [ ] **Step 4: 통과 확인**

Run: `python -m pytest tests/test_ui_contract.py::test_local_plan_controls_present -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add static/index.html tests/test_ui_contract.py
git commit -m "feat(plans): render + rename/delete local plans in archive"
```

---

### Task 4: 로그인 시 마이그레이션

**Files:**
- Modify: `static/index.html` (로그인 성공 블록 현재 L368-371; `migrateLocalPlans` 신규)
- Test: `tests/test_ui_contract.py`

- [ ] **Step 1: 실패 테스트 작성** — 추가:

```python
def test_migration_present():
    assert "async function migrateLocalPlans" in HTML
    assert "계정으로 옮길까요" in HTML
    assert "await migrateLocalPlans()" in HTML
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_ui_contract.py::test_migration_present -v`
Expected: FAIL (`assert "async function migrateLocalPlans" in HTML`)

- [ ] **Step 3a: 마이그레이션 함수 추가** — `deleteLocalPlan` 함수(Task 3에서 추가) 바로 다음에 삽입:

```javascript
      async function migrateLocalPlans() {
        const locals = LocalPlans.list();
        if (!locals.length) return;
        if (!confirm(`이 기기에 저장된 플랜 ${locals.length}개를 계정으로 옮길까요?`)) return;
        let failed = 0;
        for (const p of locals) {
          try {
            const resp = await fetch(`/api/plans`, { method: "POST", headers: authHeaders({ "Content-Type": "application/json" }), body: JSON.stringify({ title: p.title, destination: p.destination, content_json: p.content_json }) });
            if (resp.ok) { LocalPlans.remove(p.id); } else { failed++; }
          } catch (e) { failed++; }
        }
        if (failed > 0) alert(`${failed}개는 옮기지 못해 이 기기에 남겨둡니다.`);
      }
```

- [ ] **Step 3b: 로그인 성공 핸들러에서 호출** — 아래 기존 줄

```javascript
              currentUser = data.user; localStorage.setItem("onesown_user", JSON.stringify(currentUser));
              localStorage.setItem("onesown_token", data.access_token || "");
              updateAuthUI(); alert(`${currentUser.email}님 환영합니다!`);
```

를 다음으로 교체(마지막에 마이그레이션 + 재렌더 추가):

```javascript
              currentUser = data.user; localStorage.setItem("onesown_user", JSON.stringify(currentUser));
              localStorage.setItem("onesown_token", data.access_token || "");
              updateAuthUI(); alert(`${currentUser.email}님 환영합니다!`);
              await migrateLocalPlans(); renderSavedPlans();
```

- [ ] **Step 4: 통과 확인**

Run: `python -m pytest tests/test_ui_contract.py::test_migration_present -v`
Expected: PASS

- [ ] **Step 5: 전체 계약 테스트 + 회귀 확인 후 커밋**

Run: `python -m pytest tests/ -q`
Expected: PASS (신규 4개 포함 전부 통과)

```bash
git add static/index.html tests/test_ui_contract.py
git commit -m "feat(plans): migrate local plans to account on login"
```

---

### Task 5: 브라우저 E2E 검증 (gstack)

**Files:** 없음(검증만). 로컬 서버 `python main.py`(포트 8013) 사용.

- [ ] **Step 1: gstack 스킬로 시나리오 검증**

서버 기동(`http://127.0.0.1:8013/`) 후 gstack으로:
1. 비로그인 상태에서 워크플로우 1회 실행 → "현재 설계 저장"으로 로컬 저장 → "보관함 열기"에 카드 + "이 기기" 배지 표시 확인.
2. 로컬 카드 제목수정(프롬프트) → 제목 변경 반영 확인.
3. 두 번째 플랜 저장 후 하나 삭제 → 목록에서 사라짐 확인.
4. 로그인 → "N개를 계정으로 옮길까요?" 프롬프트 → 동의 → 서버 보관함에 반영, `LocalPlans` 비워짐(localStorage `onesown_local_plans` 빈 배열/없음) 확인.
5. 로그아웃 → 보관함이 로컬(빈 상태) 기준으로 표시되는지 확인.

- [ ] **Step 2: 결과 기록**

검증 통과/실패를 사용자에게 보고. 실패 시 systematic-debugging으로 원인 추적 후 해당 태스크 수정.

- [ ] **Step 3: 브랜치 마무리**

`superpowers:finishing-a-development-branch`로 main 병합/PR 여부를 사용자와 결정.
