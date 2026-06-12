# travel_food_agent

`travel_food_agent`는 여행지 기준 맛집과 지역 음식을 추천하는 독립 실행형 에이전트입니다.

## 역할

- 여행지에 맞는 맛집 후보를 찾습니다.
- 지역 음식과 대표 메뉴를 함께 보여줍니다.
- TourAPI가 실패하면 `mock_fallback`으로 안전하게 반환합니다.

## 입력값

- `destination`
- `location`
- `days`
- `budget_level`
- `user_request`

## 출력값

- `summary`
- `destination`
- `data_source`
- `food_items`
- `food_findings`
- `recommendations`
- `debug_info`

## 데이터 소스

- `tour_api`
- `mock_fallback`

## fallback 동작

TourAPI 서비스키가 없거나, API 호출이 실패하거나, 결과가 비어 있으면 여행지 기준 mock 맛집 후보를 반환합니다.

## 실행

```bash
python3 main.py
```

## 예시

```python
from main import run

result = run({
    "destination": "제주",
    "location": "제주",
    "days": 3,
    "budget_level": "medium",
    "user_request": "제주 맛집 추천"
})

print(result)
```
