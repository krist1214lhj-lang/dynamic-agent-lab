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
    three = estimate_budget("서울", "제주", days=2, level="low", people=3)["estimated_budget"]
    two = estimate_budget("서울", "제주", days=2, level="low", people=2)["estimated_budget"]
    assert three["accommodation"] == two["accommodation"]


def test_invalid_level_falls_back_medium():
    r = estimate_budget("서울", "부산", days=1, level="bogus", people=1)
    assert r["total"] > 0
