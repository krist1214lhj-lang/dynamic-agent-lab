import pytest

import workflow_critic


@pytest.fixture(autouse=True)
def _no_anthropic(monkeypatch):
    # 테스트는 실제 LLM 호출 없이 결정적으로 동작(rule_only).
    # 동적 로드 에이전트가 load_dotenv(override=True)로 키를 되살리므로,
    # 환경변수 제거만으로는 부족해 _call_anthropic 자체를 무력화한다.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(workflow_critic, "_call_anthropic", lambda *a, **k: None)
