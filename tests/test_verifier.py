from validators.travel_verifier import verify_results


def _res(agent, **kw):
    d = {"agent": agent}; d.update(kw); return d


def test_day_trip_excludes_lodging():
    inp = {"destination": "속초", "days": 1, "travel_format": "당일치기"}
    kept, excluded = verify_results(inp, [_res("travel_lodging_agent", lodging_items=[]), _res("travel_food_agent")])
    assert "travel_lodging_agent" not in [k["agent"] for k in kept]
    assert any(e["reason"] == "day_trip_no_lodging" for e in excluded)


def test_schedule_day_mismatch_excluded():
    inp = {"destination": "속초", "days": 3, "travel_format": "자유여행"}
    kept, excluded = verify_results(inp, [_res("travel_schedule_agent", daily_itinerary=[{"day": 1}])])
    assert not kept and excluded[0]["reason"] == "schedule_day_mismatch"


def test_real_api_verified_mock_estimated():
    inp = {"destination": "제주", "days": 2}
    kept, _ = verify_results(inp, [_res("travel_weather_agent", data_source="kma_api"),
                                   _res("travel_food_agent", data_source="mock_plus_conditions")])
    st = {k["agent"]: k["verification"] for k in kept}
    assert st["travel_weather_agent"] == "verified" and st["travel_food_agent"] == "estimated"


def test_agent_error_excluded():
    kept, excluded = verify_results({"destination": "부산", "days": 2}, [_res("travel_tour_agent", data_source="error")])
    assert not kept and excluded[0]["reason"] == "agent_error"
