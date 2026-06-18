import json
import os

MODEL = "claude-haiku-4-5"


def _build_prompt(conditions, results):
    cards = [{"agent": r.get("agent"), "summary": r.get("summary", ""), "verification": r.get("verification")}
             for r in results]
    return (
        "당신은 여행 설계 결과를 검증하는 비평가입니다. 아래 '선택 조건'에 비춰 각 결과 카드가 적합한지 "
        "비판적으로 판단하세요.\n"
        "규칙: 주어진 카드 중에서만 유지(keep)/제외(drop)를 정합니다. 새 항목을 만들지 마세요. "
        "조건과 무관하거나 모순되는 카드를 drop하고 한국어 사유를 답니다.\n"
        f"선택 조건: {json.dumps(conditions, ensure_ascii=False)}\n"
        f"결과 카드: {json.dumps(cards, ensure_ascii=False)}\n"
        'JSON만 출력: {"keep":["agent",...],"drop":[{"agent":"...","reason":"..."}],'
        '"final_summary":"...","match_notes":["..."]}'
    )


def _call_anthropic(prompt, timeout=8.0):
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key, timeout=timeout)
        msg = client.messages.create(model=MODEL, max_tokens=1024,
                                     messages=[{"role": "user", "content": prompt}])
        return "".join(getattr(b, "text", "") for b in msg.content if getattr(b, "type", None) == "text")
    except Exception:
        return None


def _parse_critique(raw, valid_agents):
    if not raw:
        return None
    try:
        data = json.loads(raw[raw.index("{"):raw.rindex("}") + 1])
    except (ValueError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or "keep" not in data:
        return None
    keep = [a for a in data.get("keep", []) if a in valid_agents]
    drop = [d for d in data.get("drop", []) if isinstance(d, dict) and d.get("agent") in valid_agents]
    return {"keep": keep, "drop": drop,
            "final_summary": data.get("final_summary", ""), "match_notes": data.get("match_notes", [])}


def critique(conditions, results, _caller=None):
    """(final_results, dropped, final_summary, engine). engine 'rule+llm' 성공, 'rule_only' fallback."""
    caller = _caller or _call_anthropic  # 모듈 전역을 호출 시점에 조회(테스트에서 monkeypatch 가능)
    valid = {r.get("agent") for r in results}
    parsed = _parse_critique(caller(_build_prompt(conditions, results)), valid)
    if not parsed:
        return results, [], "", "rule_only"
    keep = set(parsed["keep"]) or valid
    final = [r for r in results if r.get("agent") in keep]
    reasons = {d["agent"]: d.get("reason", "") for d in parsed["drop"]}
    dropped = [{"agent": r.get("agent"), "stage": "llm", "reason": reasons.get(r.get("agent"), "조건 관련성 낮음")}
               for r in results if r.get("agent") not in keep]
    return final, dropped, parsed["final_summary"], "rule+llm"
