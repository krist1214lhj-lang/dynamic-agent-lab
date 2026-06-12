# travel_destination_agent

`travel_destination_agent`는 사용자의 여행 요청을 받아 여행지 추천 결과를 mock JSON으로 반환하는 독립 실행형 실험용 에이전트입니다.

실제 AI API나 외부 여행 서비스는 호출하지 않으며, `main.py` 안의 고정 예시 데이터를 기반으로 결과를 만듭니다.

## Files

- `agent.json`: 에이전트 이름, 설명, 버전, 입출력 스키마, 실행 진입점 정보를 정의합니다.
- `main.py`: `run(input_data)` 함수를 제공하고 mock 추천 결과를 반환합니다.
- `README.md`: 에이전트 역할과 사용법을 설명합니다.

## Usage

Python 코드에서 직접 호출할 수 있습니다.

```python
from main import run

result = run({
    "destination_type": "nature",
    "budget": "medium",
    "duration_days": 4,
    "season": "spring",
    "traveler_count": 2
})

print(result)
```

테스트용 예시 결과는 다음 명령으로 확인할 수 있습니다.

```bash
python main.py
```
