FEATURE_AGENT_MAP = {
    "destination": "travel_destination_agent",
    "budget": "travel_budget_agent",
    "schedule": "travel_schedule_agent",
    "weather": "travel_weather_agent",
    "tour": "travel_tour_agent",
    "transport": "travel_transport_agent",
    "food": "travel_food_agent",
    "event": "travel_event_agent",
    "planning": "travel_planning_agent",
}


def _safe_days(value):
    try:
        days = int(value)
    except (TypeError, ValueError):
        days = 3
    return max(days, 1)


def build_duration_strategy(days):
    days = _safe_days(days)
    if days == 1:
        return {
            "days": 1,
            "label": "당일치기",
            "pace": "compact",
            "recommended_tour_count": "1-2",
            "recommended_food_count": "1-2",
            "recommended_event_count": "0-1",
            "night_schedule": False,
            "lodging_required": False,
        }
    if days == 2:
        return {
            "days": 2,
            "label": "1박 2일",
            "pace": "balanced",
            "recommended_tour_count": "2-3",
            "recommended_food_count": "2-3",
            "recommended_event_count": "0-2",
            "night_schedule": True,
            "lodging_required": True,
        }
    return {
        "days": days,
        "label": f"{days - 1}박 {days}일",
        "pace": "relaxed",
        "recommended_tour_count": "3-5",
        "recommended_food_count": "3-5",
        "recommended_event_count": "1-3",
        "night_schedule": True,
        "lodging_required": True,
    }


def _requested_agent_mix(requested_features):
    mix = []
    for feature in requested_features:
        agent_name = FEATURE_AGENT_MAP.get(str(feature).strip().lower())
        if agent_name and agent_name != "travel_planning_agent" and agent_name not in mix:
            mix.append(agent_name)
    return mix


def _recommended_agent_mix(requested_features, days):
    mix = _requested_agent_mix(requested_features)
    for agent_name in [
        "travel_schedule_agent",
        "travel_transport_agent",
        "travel_weather_agent",
        "travel_food_agent",
    ]:
        if agent_name not in mix:
            mix.append(agent_name)
    if _safe_days(days) >= 2 and "travel_tour_agent" not in mix:
        mix.append("travel_tour_agent")
    return mix


def _planning_summary(destination, days, strategy, companions, themes):
    base = ""
    if days == 1:
        base = f"{destination} 당일치기는 이동 부담을 줄이고 핵심 관광지, 식사, 교통 중심으로 압축 구성하는 것이 적합합니다."
    elif days == 2:
        base = f"{destination} 1박 2일은 첫날 오후와 둘째 날 오전을 중심으로 이동, 식사, 대표 명소를 균형 있게 배치하는 것이 적합합니다."
    else:
        base = f"{destination} {strategy['label']} 여행은 권역을 나누어 관광지, 맛집, 행사와 휴식 시간을 균형 있게 구성하는 것이 적합합니다."
    
    # 추가 조건 반영
    comp_map = {"alone": "나홀로", "couple": "커플/부부", "family": "가족", "parents": "부모님", "friends": "친구"}
    theme_map = {"healing": "힐링/휴식", "activity": "액티비티", "foodie": "맛집탐방", "photo": "인생샷", "culture": "역사/문화", "shopping": "쇼핑"}
    
    comp_names = [comp_map.get(c, c) for c in companions]
    theme_names = [theme_map.get(t, t) for t in themes]
    
    extra = []
    if comp_names: extra.append(f"{', '.join(comp_names)}와(과) 함께하는")
    if theme_names: extra.append(f"{', '.join(theme_names)} 중심의")
    
    if extra:
        return f"{' '.join(extra)} {base}"
    return base


def _planning_rules(strategy, priority):
    rules = []
    if strategy["days"] == 1:
        rules = [
            "공항 또는 터미널 기준 이동시간을 최소화합니다.",
            "관광지는 1~2곳만 선택합니다.",
            "야간 일정과 숙박 일정은 제외합니다.",
        ]
    elif strategy["days"] == 2:
        rules = [
            "첫날은 도착 후 접근성이 좋은 핵심 권역에 집중합니다.",
            "둘째 날 오전에 대표 관광지와 식사를 배치하고 귀가 시간을 확보합니다.",
            "숙소와 저녁 동선을 가깝게 묶어 이동 피로를 줄입니다.",
        ]
    else:
        rules = [
            "일자별로 권역을 나누어 장거리 왕복 이동을 줄입니다.",
            "관광지, 맛집, 행사 일정을 하루 단위로 균형 있게 배치합니다.",
            "마지막 날은 귀가 교통을 고려해 여유 일정을 우선합니다.",
        ]
    
    # 우선순위 반영
    if priority == "cost": rules.append("가성비를 고려하여 무료 관람지나 로컬 맛집을 우선합니다.")
    elif priority == "quality": rules.append("이동보다는 장소의 퀄리티와 만족도를 우선하여 여유 있게 배치합니다.")
    elif priority == "distance": rules.append("동선 최적화를 통해 길 위에서 보내는 시간을 최소화합니다.")
    elif priority == "popularity": rules.append("검증된 인기 명소와 핫플레이스를 중심으로 구성합니다.")
    
    return rules


def _warnings(origin, destination, days, requested_features):
    warnings = []
    if days == 1 and origin == "서울" and destination == "제주":
        warnings.append("서울 출발 제주 당일치기는 항공편 시간에 따라 실제 체류 시간이 짧을 수 있습니다.")
    if days == 1 and "event" in requested_features:
        warnings.append("당일치기에서는 행사 일정이 이동시간과 겹치면 우선순위를 낮추는 것이 좋습니다.")
    if days == 1 and len(requested_features) >= 5:
        warnings.append("당일치기에 요청 정보가 많으면 실제 일정이 과밀해질 수 있습니다.")
    return warnings


def run(input_data):
    destination = input_data.get("destination") or input_data.get("location") or "추천 여행지"
    origin = input_data.get("origin") or "서울"
    days = _safe_days(input_data.get("days", input_data.get("duration_days", 3)))
    budget_level = input_data.get("budget_level") or input_data.get("budget") or "medium"
    requested_features = [
        str(feature).strip().lower()
        for feature in input_data.get("requested_features", [])
        if str(feature).strip()
    ]
    
    # 추가 조건 파싱
    companions = input_data.get("companions", [])
    themes = input_data.get("themes", [])
    priority = input_data.get("priority", "")
    
    strategy = build_duration_strategy(days)

    return {
        "agent": "travel_planning_agent",
        "destination": destination,
        "origin": origin,
        "budget_level": budget_level,
        "requested_features": requested_features,
        "planning_summary": _planning_summary(destination, days, strategy, companions, themes),
        "duration_strategy": strategy,
        "recommended_agent_mix": _recommended_agent_mix(requested_features, days),
        "planning_rules": _planning_rules(strategy, priority),
        "warnings": _warnings(origin, destination, days, requested_features),
        "data_source": "local_duration_rules",
    }
