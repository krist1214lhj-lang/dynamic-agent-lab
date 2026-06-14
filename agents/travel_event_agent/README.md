# travel_event_agent

`travel_event_agent`는 여행지 기준 지역 축제, 행사, 공연, 문화 이벤트를 추천하는 독립 실행형 에이전트입니다.

## 역할

- 여행지에 맞는 축제와 문화행사 후보를 찾습니다.
- TourAPI의 행사/공연/축제 `contentTypeId=15` 결과를 우선 사용합니다.
- TourAPI가 실패하거나 결과가 비어 있으면 여행지 기준 `mock_fallback`을 반환합니다.

## 입력값

- `destination`
- `location`
- `days`
- `user_request`

## 출력값

- `summary`
- `destination`
- `data_source`
- `event_items`
- `event_findings`
- `recommendations`
- `debug_info`

## 데이터 소스

- `tour_api`
- `mock_fallback`

## fallback 동작

TourAPI 서비스키가 없거나 placeholder이거나, API 호출이 실패하거나, 결과가 비어 있으면 여행지 기준 mock 행사 후보를 반환합니다. API 키 값은 출력하지 않습니다.

## 실행

```bash
python main.py
```

## 예시

```python
from main import run

result = run({
    "destination": "제주",
    "location": "제주",
    "days": 3,
    "user_request": "제주 축제 행사 추천"
})

print(result)
```
