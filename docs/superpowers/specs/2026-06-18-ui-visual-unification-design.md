# UI 시각 통일 + 차분한 선택 표시 설계

작성일: 2026-06-18
상태: 승인됨 (사용자 구두 승인 "승인, 진행해줘")

## 1. 배경 / 문제

현재 `static/index.html`은 한 페이지 안에 시각 언어가 섞여 "중구난방"이다.
- "예산으로 여행 찾기"·"보관함"이 `.archive-section`이라 평소 흐릿(opacity 0.4)하게 가운데 정렬, 나머지는 또렷한 왼쪽 정렬.
- 모서리 반경이 제각각: 입력칸 14px / 셀렉트 18px / textarea 25px / 칩 999px / 프리셋 20px, 인라인 스타일 난립.
- **선택 시 정신 사나움(핵심 불만):** 테마(10)·포함정보(9)·동행(5)·프리셋이 전부 "검정 꽉찬 반전"으로 선택 표시 → 여러 개 고르면 검은 블록이 흩어져 어지러움.
- 프리셋 카드 이모지(🍞🏕️…)가 장식적 잡음.

## 2. 목표 / 비목표

**목표**
- 폼 영역 입력/칩/프리셋 카드의 외형(반경·여백·라벨)을 하나로 통일.
- 선택 상태를 "차분한 채우기"로 변경: 연회색 배경 + 검정 글자 + ✓, 미선택은 흰 배경+옅은 테두리.
- `.archive-section` 흐림 효과 제거(항상 또렷).
- 프리셋 카드 이모지 제거(텍스트 라벨만).

**비목표 (이번 작업 제외)**
- 섹션 순서/구조 재배치(스타일 토큰만 통일).
- JS 로직·`id`·이벤트 핸들러 변경.
- 결과 카드 이미지/원형 썸네일 제거(사용자 결정: 결과 사진 유지).
- 결과 표시 컴포넌트(day-card 35px, circle 50%, info-box 25px, timeline-block) 반경 변경 — 폼이 아니므로 손대지 않아 결과 렌더 회귀 위험 제거.
- 검증 배지/토글(Phase 2 선행 필요).

## 3. 변경 상세 (모두 `static/index.html`)

### 3.1 반경 토큰
- `:root`에 `--radius: 16px` 추가.
- 폼 영역에 일괄 적용(`border-radius`를 `var(--radius)`로): `.auth-form input`(20→16), `.search-field input[type=date]/select`(18→16), `textarea#user-request`(25→16), `.checkbox-grid label`(999→16), `.preset-card`(20→16), "예산 찾기" rec 입력칸 3개(인라인 14→16).
- 액션 버튼(`#run-button`, `.nav-btn`, `.auth-btn`)은 알약(999px) 유지 — 입력/칩과 형태로 구분(의도된 일관성).

### 3.2 차분한 선택 표시
- `.checkbox-grid label:has(input:checked)`: `background: #f1f5f9; color: var(--text); border-color: var(--accent); font-weight: 600;` (기존 `background: var(--accent); color:#fff` 대체).
- 체크 표시: `.checkbox-grid label:has(input:checked)::before { content: "✓ "; font-weight: 900; }`.
- `.preset-card.active`: `background: #f1f5f9; color: var(--text); border-color: var(--accent);` (기존 검정 반전 대체).
- `.tab-btn.active`: `background: #f1f5f9; color: var(--accent); border-color: var(--accent);` (기존 검정 반전 대체). 단일 활성 탭이지만 통일감 위해 동일 톤.

### 3.3 흐림 효과 제거
- `.archive-section { opacity: 0.4; }` → `opacity: 1;`, `.archive-section:hover { opacity: 1; }` 규칙 제거(중복).

### 3.4 프리셋 이모지 제거
- `renderPresets()` 템플릿에서 `<span class="preset-emoji">${p.emoji}</span>` 제거, 라벨만 렌더.
- `PRESETS` 배열에서 `emoji` 필드 제거, `.preset-emoji` CSS 규칙 제거.

### 3.5 여백/라벨 정리
- "예산 찾기" rec 입력칸 인라인 패딩을 폼 입력과 동일(`padding:14px 18px`)하게 맞춤.

## 4. 하위호환 / 기능 보존

`id`·이벤트 핸들러·`runWorkflow`/`runRecommend`/저장·보관·댓글·평점 로직 전부 불변. 섹션 순서 불변. 따라서 기존 7개 UI 계약 테스트(요소 존재·옵션·함수)는 그대로 통과하며 모든 기능이 동일하게 동작한다.

## 5. 테스트 전략

- **계약(pytest):** 기존 `tests/test_ui_contract.py` green 유지. 추가 가드: `--radius` 토큰 존재, 차분 색(`#f1f5f9`) 존재, 프리셋 이모지(🍞 등) 부재.
- **브라우저 E2E(gstack):** 프리셋+테마 다중선택 상태 스크린샷으로 "차분해졌는지" before/after 비교, 콘솔 에러 0, 워크플로우 정상 렌더 확인.
