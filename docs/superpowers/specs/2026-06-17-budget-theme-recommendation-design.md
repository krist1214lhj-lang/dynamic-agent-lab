# 예산·테마 기반 여행 추천 시스템 설계

작성일: 2026-06-17
상태: 설계 승인됨 → 구현 예정
범위: 국내(현행과 동일). 해외는 [별도 문서](2026-06-17-international-travel-extension-design.md).

## 1. 목표
사용자가 **총 예산 · 인원수 · 여행일수 · 테마**를 입력하면, 그 조건에 맞는 **추천 목적지 후보 N개(기본 5)** 를 예상 총비용·테마 매칭 이유와 함께 제시한다. 기존 흐름("목적지 선택 → 상세 설계")과 반대 방향이며, 후보 카드에서 기존 `/run-workflow` 상세 설계로 이어진다.

## 2. 승인된 기본값
- 후보 수 **N = 5**
- 숙박 객실수 = **올림(인원 / 2)**
- 추천 수준(알뜰/적당/넉넉)은 **시스템이 자동 결정**(사용자 미선택) — 예산 내 감당 가능한 최고 수준.

## 3. 사용자 흐름
1. 새 섹션 "예산으로 여행 찾기"에서 입력: `총예산(원) · 인원수 · 여행일수(일) · 테마(다중) · (선택)출발지`.
2. "추천받기" → `POST /recommend`.
3. 후보 5개 카드 표시: `목적지 · 예상 총비용(그룹) · 감당 수준 · 매칭 테마 · 추천 이유 · 예산 대비 여유`.
4. 카드의 "이 여정 자세히 보기" → 기존 `/run-workflow` 호출(`destination, days, themes, people, origin` 전달) → 상세 설계로 연결.

## 4. 새 에이전트 `travel_recommender_agent`
기존 동적 에이전트 구조(폴더 + `agent.json` + `main.py`의 `run`)를 따른다.

### 4.1 입력 (`input_data`)
`budget_total:int, people:int, days:int, themes:list[str], origin:str|None`, 후보풀 = `SUPPORTED_DESTINATIONS`.

### 4.2 내부 로직
1. 각 후보 목적지에 대해 공용 예산모델로 **수준별(low/medium/high) 예상 총비용** 계산(인원·일수 반영, §5).
2. `affordable_level` = 예상 총비용 ≤ `budget_total`인 **최고 수준**. low도 초과면 `within_budget=false`.
3. `matched_themes` = `themes ∩ DESTINATION_PROFILES[목적지].themes`.
4. `fit_score` 계산(§4.4)으로 정렬 → 상위 N.

### 4.3 출력(정규화)
```
{
  "agent": "travel_recommender_agent",
  "data_source": "rule_based",
  "summary": "...",
  "recommendations": [
    {
      "destination": "여수",
      "est_total": "740,000원",          # affordable_level 기준(없으면 low 기준)
      "affordable_level": "medium",       # within_budget=false면 null
      "within_budget": true,
      "matched_themes": ["healing","foodie"],
      "fit_score": 0.86,
      "reason": "힐링·미식 테마에 잘 맞고, 4인 2박3일 예산 안에서 '적당하게' 수준으로 다녀올 수 있습니다."
    }
  ],
  "debug_info": { "budget_total": 1000000, "people": 4, "days": 3, "themes": [...] }
}
```

### 4.4 점수화 (`fit_score`, 0~1)
정렬 우선순위: **예산 적합 > 테마 매칭 > 여유도**. 구체식(가중합):
- `budget_fit`: `within_budget`이면 1.0, 아니면 0. (초과 후보는 항상 하단)
- `theme_fit`: `len(matched_themes) / max(1, len(themes_requested))` (테마 미입력 시 0.5 중립)
- `headroom`: `within_budget`일 때 `(budget_total - est_total)/budget_total`을 0~1로 클램프 (너무 빠듯하지 않은 여유 가점)
- `fit_score = 0.6*budget_fit + 0.3*theme_fit + 0.1*headroom`
정렬 키: `(within_budget desc, fit_score desc)`. 동점은 목적지명 안정정렬.

### 4.5 `DESTINATION_PROFILES` (초기 큐레이션, 에이전트 내 상수)
`SUPPORTED_DESTINATIONS` 13곳의 테마 태그(healing/activity/foodie/photo/culture). 초기값(추후 조정 가능):
| 목적지 | 테마 |
|--------|------|
| 서울 | culture, foodie, photo |
| 부산 | activity, foodie, photo |
| 제주 | healing, activity, photo |
| 강릉 | healing, activity, photo |
| 전주 | foodie, culture |
| 대구 | foodie, culture |
| 대전 | culture, foodie |
| 광주 | culture, foodie |
| 인천 | activity, foodie, photo |
| 여수 | healing, foodie, photo |
| 경주 | culture, photo, healing |
| 속초 | healing, activity, foodie |
| 춘천 | healing, photo, foodie |

## 5. 공용 예산모델 추출 (핵심)
현재 `agents/travel_budget_agent/main.py`에 박힌 단가표·계산을 **공용 모듈**로 분리해 budget 에이전트와 recommender가 공유한다.

### 5.1 위치/임포트
- 프로젝트 루트 `budget_model.py`(BASE_DIR). 에이전트는 import 전에 `BASE_DIR`을 `sys.path`에 보장(오케스트레이터가 BASE_DIR 기준 실행하므로 대개 이미 가능, 안전하게 명시 주입).
- 노출 함수: `estimate_budget(origin, destination, days, level, people=1, themes=None, companions=None, priority=None) -> dict`(현행 `estimated_budget`/`total` 구조 반환).

### 5.2 인원·일수 반영 규칙 (신규 명시)
기존 단가 기준 위에 인원 스케일을 더한다.
- 식비 = `meal_per_count × meal_count × people`
- 장거리 교통 = `long_distance × people`
- 지역 교통 = `local_transport_per_day × days × people`
- 체험/관광 = `tour_event_per_day × days × people`
- 숙박 = `lodging_per_night × nights × rooms`, `rooms = ceil(people/2)`
- 예비비 = `subtotal × buffer_rate`
- `people` 기본값 1 → 기존 `travel_budget_agent` 동작은 **그대로 보존**(회귀 없음). budget 에이전트는 `input_data.people`가 있으면 전달.

### 5.3 기존 budget 에이전트 영향
계산을 공용 모듈 호출로 교체. 출력 스키마·기본(1인) 결과 동일. 단, `input_data.people` 전달 시 그룹 총액 계산 가능(상세 설계 흐름에서도 인원 반영).

## 6. 엔드포인트
`POST /recommend` (인증 불필요, 읽기 전용).
- 요청: `{budget_total:int, people:int, days:int, themes:list[str], origin?:str}`
- 처리: recommender 에이전트 1개 로드·실행 → `recommendations` 반환.
- 응답: 에이전트 출력 그대로(§4.3) + `input_echo`.

## 7. 프런트엔드
- 새 입력 패널(기존 디자인 토큰 재사용): 총예산, 인원수, 일수, 테마 칩(기존 5종 재사용), 출발지(선택), "추천받기" 버튼.
- 결과: 후보 카드 그리드. 모든 출력은 `escapeHtml` 적용. "이 여정 자세히 보기" → 해당 목적지로 기존 워크플로우 실행.
- 예산 초과 후보(`within_budget=false`)는 카드 하단에 "예산 초과 OO원" 회색 표기.

## 8. 테스트
- `budget_model` 단위테스트: 인원/일수 스케일(1인=기존값, 4인·2박 등 경계), 객실수 올림.
- recommender 점수화 단위테스트: 테마 매칭, 예산 경계(딱 맞음/초과), 정렬 순서.
- smoke: `POST /recommend` 200 + `recommendations` 길이≤5 + 스키마 필드 존재.

## 9. 비범위 (YAGNI)
해외 목적지, 실시간 가격/항공권, 환율, 예산 내 일정 자동완성, 목적지 테마 자동학습(초기엔 수동 큐레이션).

## 10. 리스크 / 미해결
- `DESTINATION_PROFILES`는 수동 큐레이션 → 품질 편차. 초기 단순 태그로 시작, 추후 보정.
- 공용 모듈 import 경로: 동적 에이전트 로더 특성상 `sys.path`에 BASE_DIR 보장 필요(구현 시 검증).
- 예산모델은 추정치(mock 기반)이므로 "예상"임을 UI에 명시.
