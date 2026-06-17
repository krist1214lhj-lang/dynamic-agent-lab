# Gemini CLI 작업 검토 보고서

검토 일자: 2026-06-17  
검토 대상 브랜치: `main`  
검토 범위: 작업 트리 변경분  
변경 파일:

- `main.py`
- `static/index.html`

변경 규모:

- 2 files changed
- 343 insertions
- 285 deletions

## 요약

이번 변경은 백엔드 API 일부 축소 및 워크플로우 라우팅 복원, 프론트 결과 렌더링 대폭 개편을 포함합니다. 정적 컴파일과 기본 워크플로우 호출은 통과했지만, 기존 API 계약과 기능 일부가 회귀했습니다.

특히 `destination` 기능을 선택해도 `travel_destination_agent`가 실행되지 않는 문제가 가장 중요합니다. 또한 `/feature-map` 응답 계약 변경, Supabase 예외 처리 약화, 보관함 CRUD 축소, 프론트 `innerHTML` 렌더링의 XSS 위험이 확인되었습니다.

## 검토 결과

### 1. High - `destination` 기능 선택 시 `travel_destination_agent`가 실행되지 않음

위치: `main.py`

새 라우팅 로직의 `base_order`에 `travel_destination_agent`가 없습니다. 그래서 `requested_features: ["destination"]` 요청을 보내도 실제 선택 결과는 `["travel_planning_agent"]`뿐입니다.

재현 결과:

```text
requested_features: ["destination"]
selected_agents: ["travel_planning_agent"]
agent_results: ["travel_planning_agent"]
```

영향:

- UI의 "여행지" 체크박스가 선택되어도 여행지 추천 결과가 나오지 않습니다.
- 기존 스모크 테스트의 `busan destination` 케이스가 실패합니다.
- 기본 체크박스 구성에서도 여행지 에이전트 결과가 누락됩니다.

권장 수정:

- `base_order`에 `travel_destination_agent`를 포함하세요.
- 또는 기존처럼 `FEATURE_AGENT_MAP` 결과를 모두 선택한 뒤 순서만 안정적으로 정렬하세요.

### 2. Medium - `/feature-map` API 계약 깨짐

위치: `main.py`

기존 응답에 있던 `feature_count`가 제거되었습니다.

현재 응답:

```json
{
  "features": {
    "destination": "travel_destination_agent",
    "budget": "travel_budget_agent"
  }
}
```

기존 테스트 기대:

```text
feature_count >= 10
```

영향:

- `scripts/smoke_test.py`의 `feature map` 테스트가 실패합니다.
- 외부 소비자가 `feature_count`를 사용 중이면 호환성이 깨집니다.

권장 수정:

- `/feature-map` 응답에 `feature_count: len(FEATURE_AGENT_MAP)`를 복구하세요.

### 3. Medium - Supabase 연동 실패가 API 예외로 그대로 노출될 수 있음

위치: `main.py`

`save_plan`, `delete_plan`은 `sb` 미설정, 네트워크 실패, REST 오류를 안정적으로 처리하지 않습니다. 실제 `TestClient`로 `/api/plans` 저장 호출 시 Supabase 연결 예외가 그대로 발생했습니다.

확인된 예외 유형:

```text
requests.exceptions.ConnectionError
```

영향:

- 저장/삭제 실패 시 사용자에게 정상적인 오류 응답이 가지 않습니다.
- 운영 환경에서 일시적 네트워크 문제나 Supabase 장애가 앱 서버 오류로 전파됩니다.
- `sb`가 `None`인 환경에서는 `AttributeError`가 발생할 수 있습니다.

권장 수정:

- `sb` 미설정 시 명확한 503 또는 500 응답을 반환하세요.
- Supabase 요청에는 `try/except requests.RequestException` 처리를 추가하세요.
- `insert`, `delete`, `select`가 실패 이유를 버리지 않도록 오류 응답을 표준화하세요.

### 4. Medium - 저장 보관함 기능 축소/회귀

위치:

- `main.py`
- `static/index.html`

다음 기능이 제거되거나 축소되었습니다.

- 서버 `PATCH /api/plans/{plan_id}` 제거
- 프론트 저장 플랜 제목 수정 기능 제거
- 비로그인 로컬 저장 흐름 제거
- 로그인 후 로컬 플랜 마이그레이션 흐름 제거

영향:

- 기존 저장 보관함 UX가 후퇴했습니다.
- 비로그인 사용자는 더 이상 로컬 보관함을 사용할 수 없습니다.
- 기존 로컬 저장 데이터가 있더라도 로그인 후 서버로 이전되지 않습니다.

권장 수정:

- 의도된 제품 변경인지 먼저 확인하세요.
- 의도된 변경이 아니라면 `PATCH` API와 프론트 수정/로컬 저장/마이그레이션 흐름을 복구하세요.

### 5. Medium - 프론트 `innerHTML` 렌더링에 XSS 위험 존재

위치: `static/index.html`

`destination`, `summary`, `recommendations`, 저장 플랜 `title` 등 서버 또는 사용자 입력이 여러 곳에서 escape 없이 `innerHTML`에 삽입됩니다.

위험 예:

- `displayWorkflowResult`의 `dest`
- 각 agent result의 `summary`
- `recommendations`
- 저장 플랜 `p.title`
- 저장된 `content_json` 기반 inline `onclick`

영향:

- Supabase에 저장된 제목이나 결과 JSON이 오염되면 스크립트 삽입이 가능합니다.
- 댓글은 일부 escape 처리되어 있지만 렌더링 정책이 일관되지 않습니다.

권장 수정:

- 모든 사용자/서버 입력 출력에 `escapeHtml`을 적용하세요.
- 가능하면 `innerHTML` 대신 DOM API 기반 렌더링으로 전환하세요.
- inline `onclick`에 JSON을 직접 넣는 방식은 피하세요.

### 6. Low - 교통 카드 CSS 오타

위치: `static/index.html`

현재 코드:

```css
flex-wrap:gap:20px;
```

의도된 코드:

```css
flex-wrap: wrap;
gap: 20px;
```

영향:

- 교통 카드의 버튼/텍스트 줄바꿈과 간격이 의도대로 동작하지 않을 수 있습니다.

## 검증 내역

### 정적 컴파일

명령:

```powershell
python -m py_compile main.py validators\travel_validator.py agents\travel_schedule_agent\main.py
```

결과: 통과

### FastAPI TestClient 확인

확인 항목:

- `/health`: 200
- `/agent-library`: 200
- `/feature-map`: 200, 단 `feature_count` 없음
- `/run-workflow` 기본 흐름: 200
- `/run-workflow` with `requested_features: ["destination"]`: 200, 단 `travel_destination_agent` 누락

### 기존 스모크 테스트

명령:

```powershell
python scripts\smoke_test.py
```

결과:

```text
command timed out
```

원인:

- 스모크 테스트는 실행 중인 서버 `http://localhost:8013`을 전제로 합니다.
- 현재 세션에서는 해당 서버가 실행 중이지 않아 타임아웃되었습니다.

## 권장 수정 순서

1. `travel_destination_agent` 라우팅 누락을 먼저 수정하세요.
2. `/feature-map`의 `feature_count`를 복구하세요.
3. Supabase API 예외 처리를 일관되게 정리하세요.
4. 보관함 수정/로컬 저장 제거가 의도인지 확정하고, 의도가 아니라면 기존 CRUD 흐름을 복구하세요.
5. 프론트 렌더링의 escape 정책을 정리해 XSS 위험을 줄이세요.
6. CSS 오타를 수정하세요.

## 결론

현재 변경은 일부 워크플로우 실행 자체는 가능하지만, 기존 기능 계약과 사용자 기능이 여러 군데에서 회귀했습니다. 특히 `destination` 에이전트 누락과 `/feature-map` 계약 변경은 테스트 실패로 바로 이어지는 문제이므로 우선 수정이 필요합니다.
