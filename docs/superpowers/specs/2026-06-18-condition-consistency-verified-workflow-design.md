# 조건 정합 + 자기검증 워크플로우 설계

작성일: 2026-06-18
상태: 승인됨 (사용자 구두 승인 — 하이브리드/제외/Haiku 결정 후 "오케이")

## 1. 배경 / 문제

현재 워크플로우는 에이전트가 전부 규칙 기반이고, 출력의 **조건 정합성 검증/관련성 필터가 없다.**
- UI가 `requested_features`를 기본 전부 체크로 전송 → "하루 미식여행"을 선택해도 숙박·전 영역 카드가 그대로 나온다.
- 선택 조건(`travel_format`/`themes`/`pace`)이 어떤 카드를 **보여줄지/뺄지**에 반영되지 않는다.
- 결과가 조건과 어긋나도(예: 당일치기인데 숙박, 테마 무관 행사) 걸러지지 않는다.

목표: 최종 출력이 선택 조건에 정합하도록, **규칙 게이트 + LLM 비판**의 2단 자기검증을 거쳐 무관·불일치 카드를 **제외**하고, 무엇을 왜 제외했는지 보고한다.

## 2. 목표 / 비목표

**목표**
- 에이전트 실행 결과를 응답 직전 2단 게이트로 검증·필터.
- 조건 무관/정합성 실패 카드는 최종 출력에서 **제외(숨김)**.
- 각 생존 카드에 검증 상태(`verified`/`estimated`) 부여.
- 자기검증 결과(`verification_report`: engine·제외목록·요약)를 응답·UI에 노출.
- 키 부재/실패 시 규칙만으로 graceful 동작.

**비목표 (이번 작업 제외)**
- 에이전트 실행 자체를 조건으로 가지치기(에이전트는 전부 실행해 상호 컨텍스트 유지; 게이트는 출력 단계에서만).
- 새 외부 데이터 연동(food/event/lodging은 계속 mock).
- 결과 카드 이미지/링크 변경.
- 해외 목적지.

기존 미구현 "Phase 2 검증게이트 / Phase 3 검증배지" 계획을 본 설계가 **흡수·대체**한다.

## 3. 아키텍처 / 흐름

```
run_workflow:
  에이전트 실행(현행) → validate_and_correct(현행 보정)
    → [1단] verify_results(input_data, results)          # 규칙, 결정적
    → [2단] critique_results(conditions, survivors)       # LLM(Haiku), 선택적
    → verification_report 조립 → 응답
```

에이전트 실행과 `validate_and_correct`(제주 교통 보정·과거행사 필터·중복 제거)는 **그대로 둔다.** 게이트는 그 뒤에 붙는 순수 후처리다.

## 4. 컴포넌트

### 4.1 `validators/travel_verifier.py` (신규, LLM 없음, 순수 함수)
입력: `input_data`(조건), `agent_results`(보정 후). 출력: `(kept, excluded, statuses)`.

**정합성 검사**(카드별, 실패 시 제외 후보):
- destination: 카드의 `destination`/언급이 입력 목적지와 일치.
- schedule: `daily_itinerary` 길이 == 요청 `days`.
- budget: `estimated_budget.total` > 0 그리고 항목 합과 일치(±반올림 허용).
- weather: `location`/`destination` == 입력 목적지.
- transport: 출발/도착이 `origin`/`destination`과 일치.
- 공통: 에이전트 결과 `data_source == "error"` → 제외.

**결정적 관련성 제외 규칙:**
- `travel_format == "당일치기"` → `travel_lodging_agent` 카드 제외(사유 `day_trip_no_lodging`).
- 향후 규칙 추가 가능하도록 `RELEVANCE_RULES` 테이블로 분리.

**검증 상태 부여**(생존 카드):
- `verified`: 실API 계열(`travel_tour_agent`=tour_api, `travel_weather_agent`=kma_api, `travel_transport_agent`=odsay_api, `travel_destination_agent`=tour_api)의 `data_source`가 실제 API이고 정합성 통과.
- `estimated`: 그 외(계산형 budget/schedule/planning, mock food/event/lodging, *_fallback)로 정합성 통과.
- 정합성 실패 → 제외(상태 `failed`, report에만 기록).

코어 카드(budget/schedule/weather/transport/destination/planning)는 1단에서 정합성 실패가 아닌 한 함부로 제외하지 않는다(테마 무관 미세 판단은 2단).

### 4.2 `workflow_critic.py` (신규, Anthropic Haiku 4.5)
- 클라이언트: `anthropic` SDK, `os.getenv("ANTHROPIC_API_KEY")`, 모델 `claude-haiku-4-5`.
- 입력: 조건 요약(travel_format·themes·pace·destination·days·budget_level) + 1단 생존 카드 요약(agent, summary, 대표 items 일부, verification).
- 프롬프트 규칙: "주어진 카드 중에서만 유지/제외를 결정. 새 항목을 만들지 말 것. 선택 조건과 무관하거나 모순되는 카드를 제외하고 사유를 한국어로." 출력은 JSON만:
  ```json
  { "keep": ["travel_food_agent", ...],
    "drop": [{"agent":"travel_event_agent","reason":"미식 테마와 무관한 일반 행사"}],
    "final_summary": "...", "match_notes": ["..."] }
  ```
- 파싱: JSON 추출 실패/스키마 불일치 → 비평 무시(생존 카드 전체 유지), `engine="rule_only"`.
- 적용: 최종 카드 = 1단 생존 ∩ `keep`. `drop`은 report에 stage=`llm`으로 병합. `final_summary`로 응답 `final_summary` 대체.
- **안전장치:** `anthropic` 패키지 import 실패, `ANTHROPIC_API_KEY` 미설정, 호출 예외, 타임아웃(예: 8s) → 즉시 1단 결과 사용, `engine="rule_only"`. `anthropic`은 모듈 상단이 아니라 함수 내부에서 lazy import(try/except)하여 미설치 시에도 앱이 동작. `requirements.txt`에 `anthropic` 추가(설치 권장이되 없어도 fallback).

### 4.3 `main.py` 통합
- `.env`에서 `ANTHROPIC_API_KEY` 로드(이미 load_dotenv 사용).
- `run_workflow`에서 `validate_and_correct` 다음에 verifier→critic 호출, `agent_results`를 최종 생존분으로 교체, `verification_report` 응답 추가(`WorkflowResponse`에 필드 추가, 기본값으로 하위호환).

### 4.4 `static/index.html`
- 결과 상단에 "검증 요약" 블록: `verification_report.summary` + "제외 N건" + 제외 목록(agent·사유) 접이식.
- 카드 렌더는 현행 유지(서버가 이미 생존분만 보냄). 각 카드에 작은 `verified/estimated` 배지(선택적, 톤은 통일 스타일).

## 5. 응답 스키마 (추가)
```
verification_report: {
  engine: "rule+llm" | "rule_only",
  excluded: [ { agent, stage: "rule"|"llm", reason } ],
  kept: [ { agent, verification: "verified"|"estimated" } ],
  summary: "<critic 또는 규칙 요약>"
}
```
`agent_results`는 생존 카드만 포함하고 각 항목에 `verification` 필드를 갖는다. 필드 부재 시 UI는 표시만 생략(하위호환).

## 6. 하위호환 / 실패 모드
- `ANTHROPIC_API_KEY` 없음 → `rule_only`, 200 정상, 규칙 게이트만 적용.
- 1단은 항상 동작(결정적). 2단은 best-effort.
- 신규 필드는 추가형이라 기존 호출/smoke 깨지 않음. 제외 규칙이 적용돼 카드 수가 줄 수 있으나 smoke는 엔드포인트 200·구조만 검사하도록 유지.

## 7. 테스트 전략
- **단위(verifier):** 당일치기→숙박 제외, schedule 일수 불일치→제외, budget 합 불일치→제외, 실API 데이터→verified·mock→estimated. 결정적, LLM 무관.
- **단위(critic):** JSON 파싱 성공/실패, 키 없을 때 rule_only fallback, keep/drop 적용(가짜 응답 주입으로 네트워크 없이).
- **통합:** `/run-workflow`가 `verification_report` 반환; 키 없는 환경에서 200·`rule_only`; "당일치기" 요청 시 숙박 카드 부재.
- **smoke:** 15/15 유지(키 없는 env → rule_only).
- **브라우저 E2E:** "당일치기 + 미식" 선택 → 숙박 빠지고 미식 중심 카드만, 검증 요약·제외 사유 노출.

## 8. 단계화 (plan에서 구체화)
- **Phase A:** `travel_verifier.py`(규칙 게이트) + `main.py` 통합 + 응답필드 + 단위/통합 테스트. (LLM 없이도 "당일치기→숙박 제외", 정합성 제외 동작.)
- **Phase B:** `workflow_critic.py`(Haiku) + fallback + 단위 테스트 + 통합.
- **Phase C:** UI 검증요약/배지 + 브라우저 E2E.

## 9. 사용자 작업
- 로컬 `.env`에 `ANTHROPIC_API_KEY` 추가 — **완료.**
- 프로덕션: Vercel 환경변수에 `ANTHROPIC_API_KEY` 추가 후 재배포(미적용 시 prod는 rule_only).
- `.env.example`에 문서용 줄 추가(구현 시).
