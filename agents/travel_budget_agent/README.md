# travel_budget_agent

`travel_budget_agent`는 사용자의 여행 요청을 받아 여행 예산, 비용 절감 포인트, 예상 지출 항목을 mock JSON으로 반환하는 독립 실행형 실험용 에이전트입니다.

실제 AI API나 외부 가격 조회 서비스는 호출하지 않으며, `main.py`의 고정 계산 로직과 예시 데이터를 사용합니다.

## Files

- `agent.json`: 에이전트 이름, 설명, 버전, 입출력 스키마, 실행 진입점 정보를 정의합니다.
- `main.py`: `run(input_data)` 함수를 제공하고 mock 예산 결과를 반환합니다.
- `README.md`: 에이전트 역할과 사용법을 설명합니다.

## Usage

Python 코드에서 직접 호출할 수 있습니다.

```python
from main import run

result = run({
    "destination": "Da Nang",
    "duration_days": 5,
    "traveler_count": 2,
    "budget_level": "medium",
    "travel_style": "standard"
})

print(result)
```

테스트용 예시 결과는 다음 명령으로 확인할 수 있습니다.

```bash
python3 main.py
```
