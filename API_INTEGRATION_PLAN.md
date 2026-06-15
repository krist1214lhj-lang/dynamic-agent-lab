# Travel API Integration Plan

## 1. 전체 요약 표

| agent name | 현재 data_source | 실제 API 필요 여부 | 현재 API 연결 여부 | 필요한 API 후보 | 필요한 환경변수 | fallback 유지 여부 | 우선순위 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| travel_weather_agent | kma_api, mock_fallback | 예 | 연결됨. 기상청 단기예보 API 호출 후 실패 시 fallback | 기상청 단기예보 API | KMA_SERVICE_KEY | 예 | 이미 연결됨, 점검 대상 |
| travel_tour_agent | tour_api, mock_fallback | 예 | 연결됨. TourAPI 관광지 area/keyword 조회 경로 보유 | TourAPI 관광지 조회 | TOUR_API_SERVICE_KEY | 예 | 이미 연결됨, 점검 대상 |
| travel_food_agent | tour_api, mock_fallback | 예 | 연결됨. TourAPI contentTypeId=39 음식점 조회 경로 보유 | TourAPI 음식점 조회 | TOUR_API_SERVICE_KEY | 예 | 이미 연결됨, 점검 대상 |
| travel_event_agent | tour_api, mock_fallback | 예 | 연결됨. TourAPI contentTypeId=15 행사/축제 조회 경로 보유 | TourAPI 행사/축제 조회 | TOUR_API_SERVICE_KEY | 예 | 이미 연결됨, 점검 대상 |
| travel_transport_agent | odsay_api, rule_based_fallback, mock_fallback | 예 | 연결됨. ODsay 대중교통 길찾기를 우선 호출하고 제주/섬은 island_air_sea 규칙 우선 | 1순위 ODsay 대중교통 길찾기 API, 2순위 카카오모빌리티 자동차 길찾기 API, 3순위 네이버 Maps Directions / Geocoding | ODSAY_API_KEY, KAKAO_MOBILITY_API_KEY 또는 KAKAO_REST_API_KEY, NAVER_MAPS_CLIENT_ID, NAVER_MAPS_CLIENT_SECRET | 예 | 1순위 구현됨, 점검 대상 |
| travel_destination_agent | mock_fallback | 선택 | 미연결. mock/rule 기반 목적지 추천 | TourAPI 기반 지역/키워드 추천 | TOUR_API_SERVICE_KEY | 예 | 2순위 |
| travel_budget_agent | mock_fallback | 선택 | 미연결. mock/rule 기반 예상 비용 계산 | 국내여행 규칙형 계산, 해외여행 확장 시 환율 API | 추후 결정 | 예 | 3순위 |
| travel_schedule_agent | mock_fallback | 직접 API 대상 아님 | 직접 API 없음. 다른 에이전트 결과를 조합해 일정 생성 | 없음 | 없음 | 예 | 직접 API 대상 아님 |
| travel_planning_agent | local_duration_rules | 직접 API 대상 아님 | 직접 API 없음. 전체 계획 총괄/기간 전략/에이전트 조합 판단 | 없음 | 없음 | 예 | 직접 API 대상 아님 |

## 2. 에이전트별 판단

### travel_weather_agent

- 실제 API 필요: 예.
- 현재 상태: 기상청 API 연결 여부 확인 완료. `KMA_SERVICE_KEY`를 읽어 기상청 단기예보 API를 호출한다.
- 현재 동작: 성공 시 `data_source`는 `kma_api`, 키 누락/의존성 누락/HTTP 오류/파싱 오류/빈 응답이면 `mock_fallback`.
- 필요한 환경변수: `KMA_SERVICE_KEY`.
- fallback 유지: 예.
- 우선순위: 이미 연결됨, 점검 대상.

### travel_tour_agent

- 실제 API 필요: 예.
- 현재 상태: TourAPI 관광지 연결 여부 확인 완료. area 기반 조회와 키워드 검색 경로가 있다.
- 현재 동작: 성공 시 `data_source`는 `tour_api`, 실패 시 `mock_fallback`.
- 필요한 환경변수: `TOUR_API_SERVICE_KEY`.
- 참고: 현재 코드에는 `TOURAPI_SERVICE_KEY`, `KTO_SERVICE_KEY`, `TOUR_SERVICE_KEY` alias도 있으나, 프로젝트 표준 변수는 `TOUR_API_SERVICE_KEY`로 유지한다.
- fallback 유지: 예.
- 우선순위: 이미 연결됨, 점검 대상.

### travel_food_agent

- 실제 API 필요: 예.
- 현재 상태: TourAPI `contentTypeId=39` 연결 여부 확인 완료. `areaBasedList2` 우선, 결과가 없으면 `searchKeyword2` 보조 검색을 사용한다.
- 현재 동작: 성공 시 `data_source`는 `tour_api`, 키 누락/placeholder 키/의존성 누락/빈 결과/HTTP 오류/파싱 오류면 `mock_fallback`.
- 필요한 환경변수: `TOUR_API_SERVICE_KEY`.
- fallback 유지: 예.
- 우선순위: 이미 연결됨, 점검 대상.

### travel_event_agent

- 실제 API 필요: 예.
- 현재 상태: TourAPI `contentTypeId=15` 연결 여부 확인 완료. 행사/공연/축제 후보를 `areaBasedList2`와 `searchKeyword2`로 조회한다.
- 현재 동작: 성공 시 `data_source`는 `tour_api`, 실패 시 `mock_fallback`.
- 필요한 환경변수: `TOUR_API_SERVICE_KEY`.
- fallback 유지: 예.
- 우선순위: 이미 연결됨, 점검 대상.

### travel_transport_agent

- 실제 API 필요: 예.
- 현재 상태: ODsay 대중교통 길찾기 API 연결 완료. 제주/섬 이동은 `island_air_sea` 규칙을 ODsay보다 우선하며, ODsay 키 누락/호출 실패/파싱 실패/좌표 누락 시 기존 mock/rule fallback으로 반환한다.
- API 후보:
  1. ODsay 대중교통 길찾기 API.
  2. 카카오모빌리티 자동차 길찾기 API.
  3. 네이버 Maps Directions / Geocoding.
- 필요한 환경변수:
  - `ODSAY_API_KEY`
  - `KAKAO_MOBILITY_API_KEY` 또는 `KAKAO_REST_API_KEY`
  - `NAVER_MAPS_CLIENT_ID`
  - `NAVER_MAPS_CLIENT_SECRET`
- fallback 유지: 예.
- 우선순위: 1순위 구현됨, 점검 대상.

### travel_destination_agent

- 실제 API 필요: 선택.
- 현재 상태: mock/rule 기반인지 확인 완료. 실제 TourAPI 호출은 아직 없다.
- API 후보: TourAPI 기반 지역/키워드 추천.
- 필요한 환경변수: `TOUR_API_SERVICE_KEY`.
- fallback 유지: 예.
- 우선순위: 2순위.

### travel_budget_agent

- 실제 API 필요: 선택.
- 현재 상태: mock/rule 기반인지 확인 완료. 실제 가격/환율 API 호출은 아직 없다.
- API 후보:
  - 국내여행은 우선 규칙형 계산.
  - 해외여행 확장 시 환율 API 검토.
- 필요한 환경변수: 추후 결정.
- fallback 유지: 예.
- 우선순위: 3순위.

### travel_schedule_agent

- 직접 API 대상 아님.
- 현재 상태: `duration_strategy`와 일정 템플릿으로 일정을 생성한다.
- 권장 방향: `travel_tour_agent`, `travel_food_agent`, `travel_event_agent`, `travel_transport_agent`, `travel_weather_agent` 결과를 조합해 일정 품질을 높인다.
- 필요한 환경변수: 없음.
- fallback 유지: 예.

### travel_planning_agent

- 직접 API 대상 아님.
- 현재 상태: 전체 계획 총괄, 기간 전략, 에이전트 조합 판단을 local rule로 수행한다.
- 권장 방향: API 호출보다는 입력 조건과 선택 feature에 따른 orchestration 품질 개선이 우선이다.
- 필요한 환경변수: 없음.
- fallback 유지: 예.

## 3. API 연결 우선순위

1. `travel_transport_agent` + ODsay
   - 국내 여행 플랜에서 대중교통, 환승, 버스, 지하철, 도보 연결은 사용자가 바로 체감하는 핵심 정보다.
   - ODsay 1차 API 연결은 완료되었고, 실패 시 기존 규칙형 결과를 유지한다.
2. `travel_destination_agent` + TourAPI 지역/키워드 추천
   - 목적지 추천을 mock에서 실제 지역/키워드 기반 추천으로 개선한다.
   - `TOUR_API_SERVICE_KEY`를 기존 TourAPI 계열 에이전트와 공유할 수 있다.
3. `travel_budget_agent` 규칙형 계산 고도화
   - 국내여행은 API보다 교통/숙박/식비/활동비 단가 테이블 기반 계산이 먼저다.
   - 해외여행 확장 단계에서 환율 API를 검토한다.
4. 기존 API 연결 에이전트 품질 개선
   - `weather`
   - `tour`
   - `food`
   - `event`

## 4. travel_transport_agent 권장 방향

우선 ODsay를 1차로 적용한다.

이유:

- 여행 앱에서는 자동차 경로보다 대중교통, 환승, 버스, 지하철, 도보 연결이 중요하다.
- ODsay는 국내 대중교통 길찾기에 적합하다.
- 제주/섬 지역은 ODsay 결과가 부족할 수 있으므로 기존 `island_air_sea` 규칙을 유지한다.

적용 원칙:

- `ODSAY_API_KEY`가 있으면 ODsay 호출.
- `ODSAY_API_KEY`가 없거나 ODsay 호출이 실패하면 기존 `mock_fallback` 유지.
- 서울 -> 제주, 부산 -> 제주 등 섬 이동은 항공/선박 규칙 우선.
- API 키 원문은 절대 응답에 노출하지 않는다.
- `debug_info`에는 `env_key_valid`, `fallback_reason`, `data_source`만 기록한다.
- ODsay 결과를 붙일 때도 `origin`, `destination`, `transport_profile`, `routes`, `transport_tips`, `risks`의 기존 응답 형태는 최대한 유지한다.

후순위 API 검토:

- 카카오모빌리티 자동차 길찾기 API는 렌터카/자가용 이동 계획이 필요한 경우 2순위로 검토한다.
- 네이버 Maps Directions / Geocoding은 주소 정규화, 좌표 변환, 지도 기반 보조 경로가 필요할 때 3순위로 검토한다.

## 5. 로컬/Vercel 환경변수 정책

- API 키는 로컬 `.env`에만 저장한다.
- `.env`는 GitHub에 올리지 않는다.
- `.env.example`에는 placeholder만 작성한다.
- Vercel에는 Environment Variables로 별도 등록한다.
- API 키가 없으면 `mock_fallback`으로 동작한다.
- `mock_fallback`이 발생하면 `debug_info.fallback_reason`에 이유를 남긴다.
- API 키 값 자체는 절대 응답에 노출하지 않는다.
- 키 존재 여부는 boolean 또는 `key_length`만 표시한다.
- 로컬과 Vercel의 `data_source`가 다르면 완료로 보고하지 않는다.
- 단, 차이 원인이 명확하고 사용자가 승인한 경우만 예외로 한다.

표준 환경변수 목록:

| 환경변수 | 사용 대상 | 상태 |
| --- | --- | --- |
| KMA_SERVICE_KEY | travel_weather_agent | 현재 사용 중 |
| TOUR_API_SERVICE_KEY | travel_tour_agent, travel_food_agent, travel_event_agent, 향후 travel_destination_agent | 현재 사용 중 |
| ODSAY_API_KEY | travel_transport_agent | 현재 사용 중 |
| KAKAO_MOBILITY_API_KEY 또는 KAKAO_REST_API_KEY | 향후 travel_transport_agent 자동차 길찾기 보조 | 후보 |
| NAVER_MAPS_CLIENT_ID | 향후 travel_transport_agent 지도/좌표 보조 | 후보 |
| NAVER_MAPS_CLIENT_SECRET | 향후 travel_transport_agent 지도/좌표 보조 | 후보 |
| 추후 결정 | 향후 travel_budget_agent 환율 API | 후보 |

## 6. 완료 기준

앞으로 API를 새로 붙이는 작업은 아래를 모두 만족해야 완료로 본다.

- 로컬 API 호출 성공 또는 `fallback_reason` 명확.
- Vercel API 호출 성공 또는 `fallback_reason` 명확.
- smoke test 통과.
- `verify_local_and_vercel.py` 통과.
- `data_source` 차이가 있으면 원인 설명.
- 사용자가 API 키 발급/등록이 필요한 경우 먼저 질문.
- API 키가 필요한 작업은 `.env.example`과 Vercel 환경변수 이름을 먼저 확정한 뒤 진행.
- API 키 원문이 응답, 로그, 문서, 테스트 출력에 노출되지 않는지 확인.

## 7. 감사 결론

- 이미 API가 붙은 에이전트: `travel_weather_agent`, `travel_tour_agent`, `travel_food_agent`, `travel_event_agent`.
- 아직 `mock_fallback` 또는 local rule 중심인 에이전트: `travel_destination_agent`, `travel_budget_agent`, `travel_schedule_agent`, `travel_planning_agent`.
- 바로 다음 API 통합 추천: `travel_destination_agent`에 TourAPI 지역/키워드 추천 적용.
- 운영 확인 필요: Vercel `ODSAY_API_KEY` 등록 여부, ODsay Server IP 제한 발생 여부, local/Vercel transport `data_source` 차이 발생 여부.
