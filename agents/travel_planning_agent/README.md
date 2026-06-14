# travel_planning_agent

전체 여행계획을 총괄하는 로컬 규칙 기반 에이전트입니다.

## 역할

- 여행 기간을 `당일치기`, `1박 2일`, `{days-1}박 {days}일`로 해석합니다.
- 기간에 맞는 일정 밀도, 숙박 필요 여부, 야간 일정 여부를 제안합니다.
- 요청 기능을 기준으로 후속 에이전트 조합 방향을 정리합니다.

## 입력

- `destination`
- `origin`
- `days`
- `budget_level`
- `requested_features`

## 출력

- `planning_summary`
- `duration_strategy`
- `recommended_agent_mix`
- `planning_rules`
- `warnings`

외부 API를 호출하지 않습니다.
