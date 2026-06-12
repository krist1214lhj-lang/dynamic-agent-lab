# dynamic-agent-lab

FastAPI 기반 실험용 웹앱입니다. 여행 계획 요청의 키워드를 분석해 필요한 mock 서브에이전트를 선택하고 결과를 종합합니다.

## 실행

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8011
```

브라우저에서 `http://127.0.0.1:8011`을 엽니다.

## 테스트 문장

```text
부산 2박 3일 여행지 추천과 예산, 맛집, 준비물 체크까지 알려줘
```
