# 비로그인 로컬저장 + 로그인 시 마이그레이션 설계 (G4)

작성일: 2026-06-19
상태: 승인됨 (사용자 구두 승인 "다음 진행해")

## 1. 배경 / 문제

통합 리뷰(2026-06-17)의 G4 항목 중 일부가 미구현으로 남아 있다.

- 서버 `PATCH /api/plans/{id}` 및 프런트 `renamePlan`(제목수정)은 **이미 구현됨** — G4의 "제목수정"은 완료 상태(메모 outdated였음).
- 미구현: **비로그인 사용자의 로컬 저장**과 **로그인 시 로컬 → 서버 마이그레이션**.

현재 `static/index.html` 동작:
- `saveCurrentPlan` (L477): `currentUser` 없으면 `alert("...로그인 안됨")`으로 차단 → 비로그인은 아예 저장 불가.
- `renderSavedPlans` (L483): `!currentUser`면 보관함 목록을 비움.
- 모든 저장/조회/수정/삭제가 `/api/plans` (JWT) 경로 전용.

→ 비로그인 사용자는 설계 결과를 보관할 방법이 없고, 가입 후에도 이전 결과가 사라진다.

## 2. 목표 / 비목표

**목표**
- 비로그인 상태에서 설계 결과를 `localStorage`에 저장 가능.
- 비로그인 보관함에서 로컬 플랜의 불러오기/제목수정/삭제 지원(서버 플랜과 동일한 조작성).
- 로그인 성공 직후 로컬 플랜이 있으면 확인 프롬프트 후 서버로 자동 이전, 성공분은 로컬에서 제거.

**비목표 (이번 작업 제외)**
- 서버 API 변경(기존 `/api/plans` POST 재사용, 신규 엔드포인트 없음).
- 오프라인 우선/백그라운드 동기화 레이어.
- 로컬 ↔ 서버 양방향 동기화(로그인 후엔 서버가 단일 소스).
- `comments`/`ratings` 마이그레이션(M-2, 별도 작업).

## 3. 설계 결정 (사용자 확정)

1. **마이그레이션 처리**: 로그인 직후 "로컬 플랜 N개를 계정으로 옮길까요?" 확인 → 동의 시 서버 업로드 + 로컬 제거. (무조건 자동/별도유지 아님)
2. **로컬 조작성**: 서버 플랜과 동일하게 불러오기/제목수정/삭제 전부 지원.

## 4. 아키텍처 / 접근법

선택 접근: **경량 `LocalPlans` 헬퍼 + 기존 4개 함수의 로그인 여부 분기** (A안).
localStorage 직렬화 로직을 한 곳(`LocalPlans`)에 모아 중복을 막고, 기존 인라인 스타일과 조화. (대안: 함수별 인라인 if/else — 로직 분산으로 기각. 동기화 레이어 — YAGNI로 기각.)

서버 변경 없음. 전부 `static/index.html` 내부 변경.

## 5. 데이터 모델

`localStorage["onesown_local_plans"]` = JSON 배열. 각 항목:

```json
{ "id": "local-<uuid>", "title": "...", "destination": "...", "content_json": { ... }, "created_at": "<ISO>" }
```

- `id`는 `"local-"` 접두로 서버 UUID와 구분.
- 파싱 실패 시 빈 배열로 graceful 처리(손상된 값에 앱이 죽지 않음).

## 6. 변경 상세 (모두 `static/index.html`)

### 6.1 `LocalPlans` 헬퍼 (신규)
- `list()` → 배열(파싱 실패 시 `[]`).
- `save({title, destination, content_json})` → `local-<uuid>` + `created_at` 부여해 push, 저장.
- `rename(id, title)` → 해당 항목 title 갱신.
- `remove(id)` → 해당 항목 제거.
- `clear()` / 내부 `_write(arr)`.
- uuid는 `crypto.randomUUID()` 사용(폴백: 타임스탬프+랜덤).

### 6.2 `saveCurrentPlan` 분기
- 결과 없으면 기존처럼 alert.
- `currentUser` 있으면 기존 서버 POST 경로 그대로.
- 없으면 `LocalPlans.save(...)` 후 "이 기기에 저장됨" 안내, `renderSavedPlans()`.

### 6.3 `renderSavedPlans` 분기
- 가드 변경: `if (!savedPlansExpanded) { 비움; return; }` (비로그인도 허용).
- `currentUser` 있으면 기존 서버 fetch 렌더.
- 없으면 `LocalPlans.list()`를 같은 카드 마크업으로 렌더. 컨트롤 onclick은 `renameLocalPlan(id, title)` / `deleteLocalPlan(id)`. 로컬임을 알리는 작은 라벨("이 기기") 표시.
- 비어 있으면 안내 문구.

### 6.4 로컬 조작 함수 (신규)
- `renameLocalPlan(id, currentTitle)`: prompt → `LocalPlans.rename` → 재렌더.
- `deleteLocalPlan(id)`: confirm → `LocalPlans.remove` → 재렌더.
- 불러오기는 기존 `loadSavedPlanData(content_json)` 공용 사용(변경 불필요).

### 6.5 마이그레이션 (로그인 성공 핸들러 내, L368 부근)
- 로그인 성공으로 `currentUser`/토큰 설정 직후 `migrateLocalPlans()` 호출.
- `migrateLocalPlans()`: `LocalPlans.list()`가 비면 즉시 종료. 있으면 `confirm("이 기기에 저장된 플랜 N개를 계정으로 옮길까요?")`.
  - 동의: 각 항목을 `/api/plans` POST(`authHeaders`). 성공분만 `LocalPlans.remove`. 루프 후 남은(실패) 개수 있으면 알림, 0이면 조용히 완료.
  - 거부: 로컬 유지(다음 로그인 때 다시 물음). 로컬 보관함은 로그인 상태에선 안 보이지만 데이터는 보존.
- 마지막에 `renderSavedPlans()`.

## 7. 오류 / 엣지

- 마이그레이션 부분 실패: 실패 항목만 로컬 유지 → 데이터 손실 방지.
- localStorage 용량(~5MB): 플랜 수 개 수준이라 현실적 문제 없음. 저장 예외 시 alert로 표면화.
- 손상된 localStorage 값: `list()`가 `try/catch`로 `[]` 반환.
- 로컬 id와 서버 id 충돌 없음(`local-` 접두로 분리).

## 8. 테스트 / 검증

- 순수 프런트 JS(단일 HTML)라 pytest 단위테스트 부적합 → 과거 세션과 동일하게 **gstack 브라우저 E2E**로 검증:
  1. 비로그인 저장 → 보관함에 표시.
  2. 로컬 플랜 제목수정/삭제 동작.
  3. 로그인 → 마이그레이션 프롬프트 → 동의 → 서버 보관함에 반영, 로컬 비워짐.
  4. 거부 시 로컬 유지.
- 보조: `tests/test_ui_contract.py`에 신규 식별자(`onesown_local_plans`, `LocalPlans`, `migrateLocalPlans`) 존재 어서션 추가(회귀 방지).
