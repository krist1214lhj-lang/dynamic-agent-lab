# Travel Lodging Agent

여행 기간, 목적지, 예산 수준을 기준으로 최적의 숙박시설을 추천하는 에이전트입니다.

## 주요 기능
- **TourAPI 연동**: 공공데이터포털의 TourAPI 숙박 정보(contentTypeId=32)를 사용하여 실시간 숙소 후보를 조회합니다.
- **당일치기 처리**: 1박 미만의 당일치기 여행인 경우 숙박이 불필요함을 안내합니다.
- **예산별 추천**: 사용자의 예산 수준(Low, Medium, High)에 맞춰 게스트하우스부터 고급 리조트까지 맞춤형 추천 문구를 제공합니다.
- **상세 정보 제공**: 숙소명, 주소, 전화번호, 추천 사유 등을 포함합니다.

## 입력 (Input Schema)
- `destination`: 목적지 도시 (예: 부산, 제주)
- `days`: 여행 기간 (일수)
- `budget_level`: 예산 수준 (low, medium, high)
- `requested_features`: 선택된 기능 목록

## 출력 (Output Schema)
- `agent`: 에이전트 명 (travel_lodging_agent)
- `lodging_required`: 숙박 필요 여부 (boolean)
- `lodging_nights`: 숙박 박수 (number)
- `lodging_items`: 추천 숙박 시설 목록 (array)
- `recommendations`: 에이전트의 추천 조언 (array)
- `summary`: 요약 문구 (string)

## 데이터 소스
- `tour_api`: 실제 API 연동 성공 시
- `rule_based_fallback`: 당일치기 또는 지역 코드 미지원 시
- `mock_fallback`: API 키 누락 또는 호출 실패 시
