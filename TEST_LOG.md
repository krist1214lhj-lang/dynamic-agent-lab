# TEST LOG

- 테스트 일자: 2026-06-12

## 테스트 환경

- App path: `/mnt/d/CodexWork/test-01/dynamic-agent-lab`
- Agent library: `/mnt/d/AI_AGENT_LIBRARY`
- Server: `http://localhost:8012`
- Test command: `python scripts/smoke_test.py`

## 통과 결과

- agent library: PASS
- jeju weather: PASS
- jeju transport: PASS
- busan full workflow: PASS

## GitHub clone 재현성 테스트

- 테스트 폴더: `D:\CodexWork\deploy-test\dynamic-agent-lab`
- 테스트 명령: `python scripts\smoke_test.py`
- 결과:
  - agent library: PASS
  - jeju weather: PASS
  - jeju transport: PASS
  - busan full workflow: PASS
- 결론: GitHub에서 새로 clone한 폴더에서도 내부 `agents/` 기준으로 기본 기능이 정상 작동한다.

## 현재 정상 확인된 기능

- `/agent-library` API가 6개 에이전트를 정상 반환한다.
- UI 선택값이 `/run-workflow`에 반영된다.
- 제주 날씨가 제주 기준으로 반환된다.
- 제주 교통에서 항공편과 선박이 표시된다.
- 부산 전체 실행에서 6개 에이전트가 실행된다.
- validator가 단순 오류를 보정할 수 있다.
- 화면에 에이전트 실행 흐름, 자체검증 결과, `input_data/debug_info`, 에이전트 갤러리가 표시된다.

## 다음 개선 후보

- 관광지 TourAPI 실제 결과 품질 개선
- 교통 `mock_fallback` 고도화
- UI 레이아웃 정리
- 배포 준비 전 환경변수 관리 정리
- 추가 smoke test 케이스 확대

## 주의사항

- `.env`와 API 키는 문서에 기록하지 않는다.
- 배포 전에는 `mock_fallback`과 실제 API 사용 여부를 더 명확히 표시해야 한다.
