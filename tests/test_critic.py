from workflow_critic import _parse_critique, critique


def test_parse_valid():
    raw = 'x {"keep":["a"],"drop":[{"agent":"b","reason":"무관"}],"final_summary":"s","match_notes":[]} y'
    p = _parse_critique(raw, {"a", "b"})
    assert p["keep"] == ["a"] and p["drop"][0]["agent"] == "b" and p["final_summary"] == "s"


def test_parse_invalid_returns_none():
    assert _parse_critique("not json", {"a"}) is None
    assert _parse_critique("", {"a"}) is None


def test_critique_applies_keep_drop():
    results = [{"agent": "a"}, {"agent": "b"}]
    fake = lambda prompt: '{"keep":["a"],"drop":[{"agent":"b","reason":"무관"}],"final_summary":"ok","match_notes":[]}'
    final, dropped, summary, engine = critique({}, results, _caller=fake)
    assert [r["agent"] for r in final] == ["a"]
    assert dropped[0]["agent"] == "b" and engine == "rule+llm" and summary == "ok"


def test_critique_fallback_when_no_result():
    results = [{"agent": "a"}]
    final, dropped, summary, engine = critique({}, results, _caller=lambda p: None)
    assert engine == "rule_only" and [r["agent"] for r in final] == ["a"] and dropped == []
