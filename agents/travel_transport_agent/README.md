# travel_transport_agent

`travel_transport_agent`는 사용자의 여행 요청을 받아 도시 간 이동, 현지 교통, 추천 교통수단, 교통 주의사항을 JSON으로 반환하는 실험용 에이전트입니다.

현재 버전은 실제 API를 호출하지 않고 `mock_fallback` 데이터를 반환합니다. 향후 공공 교통 API, 철도/버스 조회 API, 지도/경로 탐색 API를 연결해 실제 소요 시간, 요금, 환승 정보, 운행 상태를 채울 수 있도록 출력 구조를 유지합니다.

## Files

- `agent.json`: 에이전트 메타데이터, 입출력 스키마, 실행 함수 정의
- `main.py`: `run(input_data)` 실행 로직과 테스트용 샘플 실행 코드
- `README.md`: 에이전트 역할과 사용법

## Usage

```bash
python3 main.py
```

Windows 환경에서 `python3` 명령이 없다면 다음처럼 실행할 수 있습니다.

```bash
python main.py
```

다른 에이전트나 오케스트레이터에서는 `main.run(input_data)`를 호출하면 됩니다.

```python
from main import run

result = run({
    "origin": "서울",
    "destination": "부산",
    "days": 3,
    "travel_style": "대중교통 중심"
})
```
