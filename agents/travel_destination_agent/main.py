import json


def run(input_data):
    """Return mock travel destination recommendations without calling AI APIs."""
    destination_type = input_data.get("destination_type", "general")
    budget = input_data.get("budget", "medium")
    duration_days = input_data.get("duration_days", 3)
    season = input_data.get("season", "any")
    traveler_count = input_data.get("traveler_count", 1)

    recommendations = [
        {
            "name": "Jeju Island",
            "country": "South Korea",
            "type": "nature",
            "estimated_budget": budget,
            "recommended_days": min(max(duration_days, 3), 5),
            "highlights": ["coastal roads", "oreum trails", "local seafood"]
        },
        {
            "name": "Kyoto",
            "country": "Japan",
            "type": "culture",
            "estimated_budget": budget,
            "recommended_days": min(max(duration_days, 3), 4),
            "highlights": ["temples", "traditional streets", "seasonal gardens"]
        },
        {
            "name": "Da Nang",
            "country": "Vietnam",
            "type": "beach",
            "estimated_budget": budget,
            "recommended_days": min(max(duration_days, 4), 6),
            "highlights": ["beaches", "nearby old town", "affordable resorts"]
        }
    ]

    preferred = [
        item for item in recommendations
        if destination_type == "general" or item["type"] == destination_type
    ]
    selected = preferred if preferred else recommendations

    return {
        "agent": "travel_destination_agent",
        "summary": (
            f"Mock recommendations for a {season} {destination_type} trip "
            f"with {traveler_count} traveler(s), budget level '{budget}', "
            f"and {duration_days} day(s)."
        ),
        "recommendations": selected,
        "reasons": [
            "입력된 여행 유형과 예산을 기준으로 mock 후보를 필터링했습니다.",
            "실제 AI API나 외부 서비스 호출 없이 고정된 예시 데이터를 반환합니다.",
            "다음 단계 에이전트가 사용할 수 있도록 JSON 구조를 일정하게 유지합니다."
        ],
        "next_agents": [
            "travel_itinerary_agent",
            "hotel_recommendation_agent",
            "flight_search_agent"
        ]
    }


if __name__ == "__main__":
    sample_input = {
        "destination_type": "nature",
        "budget": "medium",
        "duration_days": 4,
        "season": "spring",
        "traveler_count": 2
    }
    print(json.dumps(run(sample_input), ensure_ascii=False, indent=2))
