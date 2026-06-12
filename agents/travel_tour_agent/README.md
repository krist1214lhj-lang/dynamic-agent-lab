# travel_tour_agent

`travel_tour_agent`는 사용자의 여행 요청을 받아 관광지, 행사, 숙박, 이미지 후보를 mock JSON으로 반환하는 독립 실행형 실험용 에이전트입니다.

현재는 `.env`에 TourAPI 서비스키가 있으면 한국관광공사 TourAPI 호출을 시도하고, 키가 없거나 호출에 실패하면 고정 예시 데이터를 `mock_fallback`으로 반환합니다. 출력 구조는 TourAPI의 관광지, 행사, 숙박, 이미지 검색 결과를 담을 수 있도록 `title`, `addr`, `category`, `image`, `mapx`, `mapy` 필드를 유지합니다.

## Files

- `agent.json`: 에이전트 이름, 설명, 버전, 입출력 스키마, 실행 진입점 정보를 정의합니다.
- `main.py`: `run(input_data)` 함수를 제공하고 mock 관광 후보를 반환합니다.
- `README.md`: 에이전트 역할과 사용법을 설명합니다.

## TourAPI Plan

`travel_tour_agent/.env`에 아래 키 중 하나를 설정하면 TourAPI 연결을 시도합니다.

```bash
TOURAPI_SERVICE_KEY=your_service_key
```

호출은 우선 `searchKeyword2`를 사용하고, 검색 키워드가 없으면 `areaBasedList2`를 사용할 수 있는 구조입니다. API 호출 실패, 키 없음, 의존성 없음, 빈 응답은 모두 `mock_fallback`으로 처리합니다.

## Usage

Python 코드에서 직접 호출할 수 있습니다.

```python
from main import run

result = run({
    "user_request": "서울에서 2박 3일 여행하며 관광지와 행사 후보를 보고 싶어.",
    "location": "서울",
    "period": "2박 3일",
    "days": 3,
    "category": "관광지"
})

print(result)
```

테스트용 예시 결과는 다음 명령으로 확인할 수 있습니다.

```bash
python3 main.py
```
