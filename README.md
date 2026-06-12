# dynamic-agent-lab

FastAPI 기반 웹앱입니다. 여행 조건을 입력하면 필요한 독립 에이전트를 자동 선택하고 실행해 결과를 통합합니다.

- UI 선택 패널과 추가 요청 입력을 함께 지원합니다.
- 외부 에이전트 라이브러리의 `travel_*` 에이전트를 로드해 결과를 통합합니다.
- 자체검증 validator로 단순 오류를 자동 보정합니다.

## 주요 기능

- UI 선택 패널
- 자동 에이전트 선택
- 에이전트 실행 흐름 표시
- 자체검증 결과 표시
- `input_data` / `debug_info` 패널
- 에이전트 라이브러리 갤러리
- smoke test 스크립트

## 폴더 구조

```text
dynamic-agent-lab/
  agents/
  main.py
  static/index.html
  validators/travel_validator.py
  scripts/smoke_test.py
  AGENT.md
  TEST_LOG.md
  README.md
  requirements.txt
```

## 외부 에이전트 라이브러리

- 기본 경로: `agents/`
- 개발용 fallback: `/mnt/d/AI_AGENT_LIBRARY`
- 외부 라이브러리 의존성을 줄이고, 배포와 재현성을 높이기 위해 필요한 `travel_*` 에이전트를 프로젝트 내부에 포함합니다.
- 포함 에이전트:
  - `travel_destination_agent`
  - `travel_budget_agent`
  - `travel_schedule_agent`
  - `travel_weather_agent`
  - `travel_tour_agent`
  - `travel_transport_agent`

## 실행 방법

### WSL/Linux

```bash
cd /mnt/d/CodexWork/test-01/dynamic-agent-lab
uvicorn main:app --host 0.0.0.0 --port 8012 --reload --reload-dir /mnt/d/CodexWork/test-01/dynamic-agent-lab --reload-dir /mnt/d/AI_AGENT_LIBRARY
```

### PowerShell

```powershell
cd D:\CodexWork\test-01\dynamic-agent-lab
uvicorn main:app --host 0.0.0.0 --port 8012 --reload
```

## 접속 주소

http://localhost:8012

## API

- `GET /`
- `POST /run-workflow`
- `GET /agent-library`

## 테스트 방법

### PowerShell

```powershell
python scripts\smoke_test.py
```

### WSL/Linux

```bash
python3 scripts/smoke_test.py
```

## 현재 smoke test 통과 항목

- agent library
- jeju weather
- jeju transport
- busan full workflow

## 보안 주의사항

- API 키와 서비스키는 `.env`로 별도 관리하고 GitHub에 올리지 않습니다.
- `.env` 파일은 GitHub에 올리지 않습니다.
- API 키나 서비스키는 README에 기록하지 않습니다.
- `.gitignore`에 `.env`, `.env.*`, `__pycache__`, `*.pyc` 등이 포함되어 있습니다.

## 현재 상태

- 초기 기능 통합 완료
- GitHub 첫 커밋 완료
- smoke test 4개 통과

## 다음 개선 후보

- 관광지 실제 API 결과 품질 개선
- 교통 `mock_fallback` 고도화
- UI 레이아웃 정리
- 배포 환경 구성
- 테스트 케이스 확대
