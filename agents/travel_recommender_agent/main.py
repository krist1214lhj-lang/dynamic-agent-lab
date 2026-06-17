import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from budget_model import estimate_budget

DESTINATION_PROFILES = {
    "서울": ["culture", "foodie", "photo"],
    "부산": ["activity", "foodie", "photo"],
    "제주": ["healing", "activity", "photo"],
    "강릉": ["healing", "activity", "photo"],
    "전주": ["foodie", "culture"],
    "대구": ["foodie", "culture"],
    "대전": ["culture", "foodie"],
    "광주": ["culture", "foodie"],
    "인천": ["activity", "foodie", "photo"],
    "여수": ["healing", "foodie", "photo"],
    "경주": ["culture", "photo", "healing"],
    "속초": ["healing", "activity", "foodie"],
    "춘천": ["healing", "photo", "foodie"],
}

LEVEL_LABEL = {"low": "알뜰하게", "medium": "적당하게", "high": "넉넉하게"}


def _safe_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _affordable(origin, dest, days, people, budget_total, themes):
    best = None
    for lvl in ("low", "medium", "high"):
        total = estimate_budget(origin, dest, days, lvl, people=people, themes=themes)["total"]
        if total <= budget_total:
            best = (lvl, total)
    low_total = estimate_budget(origin, dest, days, "low", people=people, themes=themes)["total"]
    return best, low_total


def _reason(dest, matched, within, lvl, people, days):
    parts = []
    if matched:
        parts.append(f"{', '.join(matched)} 테마에 잘 맞고")
    if within:
        parts.append(f"{people}인 {days}일 예산 안에서 '{LEVEL_LABEL.get(lvl, lvl)}' 수준으로 다녀올 수 있습니다")
    else:
        parts.append("입력하신 예산으로는 다소 빠듯합니다")
    return f"{dest}: " + ", ".join(parts) + "."


def run(input_data):
    safe = input_data if isinstance(input_data, dict) else {}
    budget_total = max(_safe_int(safe.get("budget_total"), 0), 0)
    people = max(_safe_int(safe.get("people"), 1), 1)
    days = max(_safe_int(safe.get("days"), 1), 1)
    themes = safe.get("themes") or []
    origin = safe.get("origin") or "서울"
    limit = max(_safe_int(safe.get("limit"), 5), 1)
    pool = safe.get("candidates") or list(DESTINATION_PROFILES.keys())

    recs = []
    for dest in pool:
        if dest == origin:
            continue
        best, low_total = _affordable(origin, dest, days, people, budget_total, themes)
        within = best is not None
        profile = DESTINATION_PROFILES.get(dest, [])
        matched = [t for t in themes if t in profile]
        theme_fit = (len(matched) / len(themes)) if themes else 0.5

        if within:
            lvl, est = best
            headroom = max(0.0, min(1.0, (budget_total - est) / budget_total)) if budget_total else 0.0
        else:
            lvl, est = None, low_total
            headroom = 0.0

        budget_fit = 1.0 if within else 0.0
        fit = round(0.6 * budget_fit + 0.3 * theme_fit + 0.1 * headroom, 4)

        recs.append({
            "destination": dest,
            "est_total": f"{est:,}원",
            "affordable_level": lvl,
            "within_budget": within,
            "matched_themes": matched,
            "fit_score": fit,
            "reason": _reason(dest, matched, within, lvl, people, days),
        })

    recs.sort(key=lambda r: (-(1 if r["within_budget"] else 0), -r["fit_score"], r["destination"]))
    top = recs[:limit]

    return {
        "agent": "travel_recommender_agent",
        "data_source": "rule_based",
        "summary": f"예산 {budget_total:,}원 · {people}명 · {days}일 기준 추천 {len(top)}곳",
        "recommendations": top,
        "debug_info": {"budget_total": budget_total, "people": people, "days": days, "themes": themes},
    }
