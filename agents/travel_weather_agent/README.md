# travel_weather_agent

`travel_weather_agent`는 사용자의 여행 요청을 받아 여행 기간의 날씨, 기온, 비 가능성, 여행 주의사항을 JSON으로 반환하는 독립 실행형 실험용 에이전트입니다.

이 에이전트는 기상청 단기예보 API 연결 준비 구조를 가집니다. `.env`에 `KMA_SERVICE_KEY`가 있으면 서울 기준 단기예보 API 호출을 시도하고, 키가 없거나 호출에 실패하면 기존 mock 결과와 같은 구조의 `mock_fallback`으로 동작합니다.

현재 단계에서는 구조 안정성을 우선하며, API 응답 파싱은 가능한 범위에서만 처리합니다.

## Files

- `agent.json`: 에이전트 이름, 설명, 버전, 입출력 스키마, 실행 진입점 정보를 정의합니다.
- `main.py`: `run(input_data)` 함수를 제공하고 KMA API 또는 mock fallback 날씨 정보를 반환합니다.
- `README.md`: 에이전트 역할과 사용법을 설명합니다.

## Environment

기상청 단기예보 API를 사용하려면 `travel_weather_agent/.env` 파일에 다음 값을 설정합니다.

```bash
KMA_SERVICE_KEY=your_service_key
```

`KMA_SERVICE_KEY`가 없으면 API를 호출하지 않고 `data_source`가 `mock_fallback`인 결과를 반환합니다. 실제 API 사용에 성공하면 `data_source`는 `kma_api`입니다.

## Usage

Python 코드에서 직접 호출할 수 있습니다.

```python
from main import run

result = run({
    "user_request": "서울에서 2박 3일 여행을 가려고 하는데 날씨와 준비물을 알려줘.",
    "location": "Da Nang",
    "period": "2박 3일",
    "days": 3,
    "season": "summer"
})

print(result)
```

테스트용 예시 결과는 다음 명령으로 확인할 수 있습니다.

```bash
python3 main.py
```
