# 해외여행 확장 설계 문서 (Region Provider 추상화)

작성일: 2026-06-17
상태: 설계(Design only) — **본 문서는 코드 변경을 포함하지 않습니다.** 시스템 안정화 이후 단계적 구현의 청사진입니다.
범위: 시장 중립(provider-agnostic) · 구조 중심
선정 방향: **A안 — Region Provider 추상화**

---

## 1. 배경과 목표

현재 `dynamic-agent-lab`은 **국내(대한민국) 여행 전용**입니다. 목적지, 데이터 소스(API), 통화가 모두 한국에 하드코딩되어 있습니다. 시스템이 안정화되면 **해외여행**을 추가할 예정입니다.

이 문서의 목표는 해외 기능을 **지금 구현하는 것이 아니라**, 나중에 붙일 때의 비용과 리스크를 줄이도록:
1. 현재 코드의 "국내 종속 지점"을 빠짐없이 인벤토리화하고,
2. 해외를 끼워 넣을 **확장 지점(seam)** 과 인터페이스를 정의하며,
3. 안정화 이후의 **단계별 로드맵**을 제시하는 것입니다.

비목표(Non-goals): 특정 국가 provider 선정, 실제 해외 API 연동, 통화 환산 구현, i18n 번역 — 모두 후속 단계.

---

## 2. 국내 종속 지점 인벤토리 (현재 코드 기준)

해외 확장 시 손대야 하는 지점 전수. (파일·라인은 작성 시점 기준, 이동 가능)

| # | 위치 | 국내 종속 내용 | 해외 영향 |
|---|------|---------------|-----------|
| D1 | `main.py` `SUPPORTED_DESTINATIONS` | 한국 도시 13곳 하드코딩(`서울`,`부산`,`제주`…) | 목적지 판별이 한국 도시명에만 동작 |
| D2 | `main.py` `run_workflow` | `dest` 기본값 `"서울"`, 도시명 부분일치로 목적지 추출 | 국가/언어 컨텍스트 없음 |
| D3 | `agents/travel_weather_agent/main.py` | 기상청 KMA `apis.data.go.kr/1360000/VilageFcstInfoService_2.0`, `KMA_SERVICE_KEY`, 한국 격자좌표 | 한국 외 날씨 불가 |
| D4 | `agents/travel_destination_agent/main.py` | 한국관광공사 TourAPI `KorService2`, `AREA_CODE_BY_NAME`(서울=1, 부산=6, 제주=39…), `areaCode` 파라미터 | 한국 지역코드 체계 종속 |
| D5 | `agents/travel_tour_agent/main.py` | TourAPI `KorService2` | 동일 |
| D6 | `agents/travel_lodging_agent` | `TOUR_API_SERVICE_KEY` 기반(숙소 링크는 Agoda=글로벌 호환) | 데이터는 국내, 링크만 해외 가능 |
| D7 | `agents/travel_transport_agent/main.py` | ODsay `api.odsay.com/.../searchPubTransPathT`(국내 대중교통 전용) | 해외 대중교통 경로 불가 |
| D8 | `agents/travel_budget_agent/main.py` | 단가/총액 **KRW 고정**, `LONG_DISTANCE_TRANSPORT`가 한국 도시쌍(`서울-부산` 등), 기본 origin `서울`/dest `부산` | 통화·교통비 모델이 한국 전제 |
| D9 | `agents/travel_food_agent`, `travel_event_agent` | 결과 텍스트·금액이 KRW·한국 맥락 | 통화/지역성 |
| D10 | 데이터모델 `travel_plans` | `destination` 텍스트만 저장, 국가/통화 개념 없음 | 저장 데이터에 국가 메타 부재 |

**관찰:** 모든 종속이 **에이전트 내부에 직접 박혀** 있고, 오케스트레이터(`run_workflow`)는 국가/통화 개념 없이 `input_data`만 전달합니다. 따라서 확장 핵심은 "에이전트가 데이터 소스를 직접 고르는 대신 컨텍스트로 고르게" 만드는 것입니다.

---

## 3. 핵심 개념: 국가/통화 컨텍스트 + Provider 인터페이스

### 3.1 컨텍스트 확장
오케스트레이터가 입력에서 국가를 판별해 `input_data`에 표준 필드를 실어 모든 에이전트에 전달합니다.

```
input_data = {
  ...,
  "country": "KR",        # ISO 3166-1 alpha-2 (기본 KR)
  "region": "KR-11",      # 선택: 세부 지역(ISO 3166-2 등)
  "currency": "KRW",      # ISO 4217 (country에서 파생)
  "locale": "ko-KR",      # 선택: 결과 언어/표기
}
```
- 후방호환: 필드 미존재 시 모든 에이전트는 `KR`/`KRW`로 동작(현재와 동일).
- 국가 판별 책임은 **오케스트레이터 한 곳**에 둠(에이전트는 받기만 함).

### 3.2 Provider 인터페이스 (seam)
각 "데이터 소스 의존" 에이전트는 국가별 구현을 갈아끼울 수 있는 얇은 인터페이스 뒤로 데이터 접근을 숨깁니다. 한국 구현은 현재 코드를 그대로 이전.

| 인터페이스 | 입력 | 출력(정규화) | 국내 구현 | 해외 구현(후속) |
|-----------|------|-------------|-----------|----------------|
| `WeatherProvider` | country, location, dates | `daily_forecast[]` | KMA | (미정: 글로벌 기상 API) |
| `DestinationProvider`/`TourProvider` | country, region, keyword | `recommendations[]`/`items[]` | TourAPI | (미정) |
| `TransportProvider` | country, origin, dest | `routes[]` | ODsay | (미정) |
| `LodgingProvider` | country, dest | `items[]` + 예약링크 | TourAPI+Agoda | Agoda(이미 글로벌) |
| `BudgetModel` | country, currency, days, level | `estimated_budget` | KRW 단가표 | 통화별 단가표 |

핵심 규칙: **출력 스키마는 국가와 무관하게 동일**해야 함(프런트 렌더가 그대로 동작). provider는 "어디서 가져오나"만 다르고 "무엇을 돌려주나"는 같음.

### 3.3 통화 처리
- 금액은 내부적으로 `{amount, currency}`로 다루고, 표시 시 `currency`로 포맷.
- 환산은 후속 단계(필요 시 환율 provider). Phase 1에서는 통화 라벨만 분리(현재 KRW 하드코딩 → `currency` 필드 사용).

---

## 4. 에이전트별 확장 포인트 요약

| 에이전트 | 지금 하드코딩 | 추상화 대상 | 난이도 |
|----------|--------------|-------------|--------|
| weather | KMA 호출/격자 | `WeatherProvider` | 중 |
| destination | TourAPI/지역코드 | `DestinationProvider`(지역코드→범용 지역 식별자) | 상 |
| tour | TourAPI | `TourProvider` | 상 |
| transport | ODsay | `TransportProvider` (해외는 fallback/외부링크로 시작 가능) | 상 |
| lodging | TourAPI+Agoda | `LodgingProvider`(Agoda는 이미 글로벌) | 하 |
| budget | KRW 단가·도시쌍 | `BudgetModel`(통화별 단가표 + 일반화된 장거리 교통 추정) | 중 |
| food/event | KRW·한국 맥락 | 통화/locale 주입 | 하 |
| planning/schedule | 데이터소스 없음(조립) | 영향 적음(통화 라벨 정도) | 하 |

당일치기·fallback 정책(현재 mock_fallback)은 해외에서도 1차 안전망으로 재사용 가능 — provider 미구현 국가는 mock/외부링크로 graceful degrade.

---

## 5. 단계별 로드맵

> 각 Phase는 독립적으로 머지 가능하며, 앞 단계가 뒤 단계를 막지 않도록 후방호환 유지.

- **Phase 0 — Seam 정의 (현재, 문서)**: 본 설계 확정. 코드 변경 없음.
- **Phase 1 — 컨텍스트 스레딩**: `run_workflow`가 `country/currency/locale`을 `input_data`에 주입(기본 KR/KRW). 에이전트는 아직 동작 동일. 예산/식비 표시가 하드코딩 "원" 대신 `currency` 사용. **순수 리팩터링, 사용자 영향 0.**
- **Phase 2 — Provider 인터페이스 도입**: 데이터 의존 에이전트의 데이터 접근부를 provider 인터페이스 뒤로 이동, 한국 구현을 그 뒤로 이전. 외부 동작 불변(회귀 테스트로 보장).
- **Phase 3 — 첫 해외 provider 시범**: 가장 쉬운 축(weather 또는 lodging)부터 비한국 국가 1개 provider 추가. 데이터 없는 축은 mock/외부링크로 우회.
- **Phase 4 — 통화/지역화**: 통화 환산(환율 provider), 금액 포맷, locale별 표기. 데이터모델에 국가/통화 필드.
- **Phase 5 — UI 국가 선택**: 프런트에 국가 선택 + 국가별 가용 기능 표시. SUPPORTED_DESTINATIONS를 국가 인지형으로 교체.

각 Phase는 별도 spec→plan→구현 사이클로 진행(특히 Phase 2~3는 회귀 위험이 커 TDD 권장).

---

## 6. 데이터모델 영향 (향후)

`travel_plans`에 후속 필드(모두 nullable, 후방호환):
- `country` TEXT (ISO alpha-2, 기존 행은 NULL→`KR` 간주)
- `currency` TEXT (ISO 4217)
- (선택) `locale` TEXT

마이그레이션은 Phase 4에서 신규 `00X_*.sql`로 추가(기존 마이그레이션 불변).

---

## 7. 리스크 · 미해결 질문

- **데이터 커버리지 편차**: 국가마다 대중교통/관광 공개 API 품질이 천차만별. → provider 없는 축은 mock/외부링크 fallback을 1급 시민으로 설계.
- **지역 식별자 일반화**: 현재 TourAPI 지역코드(D4) 의존. 범용 지역 식별(좌표/도시명/geocoding)로 추상화 필요.
- **통화 환산 정확도**: 환율 변동·캐시 전략(후속).
- **i18n**: 결과 텍스트가 한국어 고정. locale 도입 시 메시지 분리 필요.
- **비용**: 해외 API는 유료/쿼터 이슈 가능 — provider별 키·rate limit 정책 필요.
- **미정 결정**: 첫 타겟 국가(현재 미정 → 구조만 중립적으로), 어떤 해외 provider를 쓸지.

---

## 8. 요약

국내 종속은 전부 에이전트 내부에 박혀 있고 오케스트레이터엔 국가 개념이 없다. 해외 확장의 비용 대부분은 "에이전트가 데이터 소스를 직접 고르는 구조"에서 나온다. 따라서 **(1) 국가/통화 컨텍스트를 오케스트레이터에서 주입하고 (2) 데이터 접근을 Provider 인터페이스 뒤로 숨기되 출력 스키마는 국가 불변으로 유지**하면, 한국 동작을 그대로 둔 채 해외를 단계적으로 끼울 수 있다. 지금은 seam 정의(Phase 0)까지만 하고, 안정화 후 Phase 1부터 후방호환으로 진행한다.
