from budget_model import estimate_budget


def test_single_person_matches_legacy_seoul_busan():
    r = estimate_budget("서울", "부산", days=3, level="medium", people=1)
    eb = r["estimated_budget"]
    assert eb["food"] == 144000
    assert eb["accommodation"] == 200000
    assert r["total"] == eb["total"]


def test_scales_with_people_and_rooms():
    one = estimate_budget("서울", "부산", days=3, level="medium", people=1)["total"]
    four = estimate_budget("서울", "부산", days=3, level="medium", people=4)["total"]
    assert four > one * 2


def test_rooms_ceil_half_people():
    # ceil(people/2): 3인과 4인은 모두 2실 → 숙박비 동일, 2인은 1실 → 더 적음
    three = estimate_budget("서울", "제주", days=2, level="low", people=3)["estimated_budget"]
    four = estimate_budget("서울", "제주", days=2, level="low", people=4)["estimated_budget"]
    two = estimate_budget("서울", "제주", days=2, level="low", people=2)["estimated_budget"]
    assert three["accommodation"] == four["accommodation"]
    assert two["accommodation"] < three["accommodation"]


def test_invalid_level_falls_back_medium():
    r = estimate_budget("서울", "부산", days=1, level="bogus", people=1)
    assert r["total"] > 0


def _transport(origin, dest, **kw):
    return estimate_budget(origin, dest, days=3, level="medium", people=1, **kw)["estimated_budget"]["transportation"]


def test_transport_differs_by_destination():
    # 서울 출발, 동일 조건이면 가까운 대전 < 먼 광주 (더 이상 동일하지 않다)
    daejeon = _transport("서울", "대전")
    gwangju = _transport("서울", "광주")
    sokcho = _transport("서울", "속초")
    assert len({daejeon, gwangju, sokcho}) == 3
    assert daejeon < gwangju


def test_jeju_uses_air_premium_from_other_origin():
    # 대구->제주(항공)는 대구->부산(육지)보다 비싸야 한다
    assert _transport("대구", "제주") > _transport("대구", "부산")


def test_explicit_seoul_busan_transport_preserved():
    # 명시 테이블 보존: long_dist 120000 + 현지교통 20000*3
    assert _transport("서울", "부산") == 120000 + 20000 * 3
