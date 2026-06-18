REAL_API_SOURCE = {
    "travel_tour_agent": "tour_api",
    "travel_weather_agent": "kma_api",
    "travel_transport_agent": "odsay_api",
    "travel_destination_agent": "tour_api",
}


def _destination(input_data):
    return input_data.get("destination") or input_data.get("location")


def _days(input_data):
    try:
        return max(int(input_data.get("days") or input_data.get("duration_days") or 3), 1)
    except (TypeError, ValueError):
        return 3


def _parse_won(value):
    if value is None:
        return None
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return int(digits) if digits else None


def _status(result):
    a = result.get("agent")
    if a in REAL_API_SOURCE and result.get("data_source") == REAL_API_SOURCE[a]:
        return "verified"
    return "estimated"


def _exclusion_reason(result, input_data):
    """결정적 제외 사유를 반환(없으면 None). 필드가 없으면 관대하게(제외 안 함)."""
    a = result.get("agent")
    if result.get("data_source") == "error":
        return "agent_error"
    if input_data.get("travel_format") == "당일치기" and a == "travel_lodging_agent":
        return "day_trip_no_lodging"
    if a == "travel_schedule_agent":
        itin = result.get("daily_itinerary")
        if isinstance(itin, list) and len(itin) != _days(input_data):
            return "schedule_day_mismatch"
    if a == "travel_budget_agent":
        total = _parse_won(result.get("total"))
        if total is not None and total <= 0:
            return "budget_nonpositive"
    if a == "travel_destination_agent":
        dest, rd = _destination(input_data), result.get("destination")
        if dest and rd and dest not in str(rd) and str(rd) not in str(dest):
            return "destination_mismatch"
    return None


def verify_results(input_data, agent_results):
    """(kept, excluded) 반환. kept 각 항목에 'verification' 부여, excluded=[{agent,stage,reason}]."""
    kept, excluded = [], []
    for r in agent_results:
        if not isinstance(r, dict) or not r.get("agent"):
            continue
        reason = _exclusion_reason(r, input_data)
        if reason:
            excluded.append({"agent": r.get("agent"), "stage": "rule", "reason": reason})
            continue
        r = dict(r)
        r["verification"] = _status(r)
        kept.append(r)
    return kept, excluded
