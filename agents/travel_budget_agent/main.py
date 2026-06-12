import json


def _money(amount):
    return f"${amount:,}"


def run(input_data):
    """Return mock travel budget data without calling AI APIs."""
    destination = input_data.get("destination", "Unknown destination")
    duration_days = int(input_data.get("duration_days", 3))
    traveler_count = int(input_data.get("traveler_count", 1))
    budget_level = input_data.get("budget_level", "medium")
    travel_style = input_data.get("travel_style", "standard")

    daily_multiplier = {
        "low": 0.75,
        "medium": 1.0,
        "high": 1.45
    }.get(budget_level, 1.0)

    transportation = int(180 * traveler_count * daily_multiplier)
    accommodation = int(90 * duration_days * traveler_count * daily_multiplier)
    food = int(35 * duration_days * traveler_count * daily_multiplier)
    activities = int(45 * duration_days * traveler_count * daily_multiplier)
    total = transportation + accommodation + food + activities

    return {
        "agent": "travel_budget_agent",
        "summary": (
            f"Mock budget estimate for {traveler_count} traveler(s) visiting "
            f"{destination} for {duration_days} day(s), using budget level "
            f"'{budget_level}' and travel style '{travel_style}'."
        ),
        "estimated_budget": {
            "transportation": _money(transportation),
            "accommodation": _money(accommodation),
            "food": _money(food),
            "activities": _money(activities),
            "total": _money(total)
        },
        "saving_tips": [
            "항공권과 숙소는 성수기 이전에 예약하면 비용을 줄일 수 있습니다.",
            "도시 교통 패스나 지역 패스를 사용하면 이동 비용을 절감할 수 있습니다.",
            "무료 관광지와 현지 식당을 함께 활용하면 전체 지출을 낮출 수 있습니다."
        ],
        "risks": [
            "성수기에는 숙박비와 교통비가 mock 예상보다 높아질 수 있습니다.",
            "환율 변동과 현지 세금은 총예산에 영향을 줄 수 있습니다.",
            "액티비티 예약 취소 수수료가 발생할 수 있습니다."
        ],
        "next_agents": [
            "travel_destination_agent",
            "travel_itinerary_agent",
            "hotel_recommendation_agent"
        ]
    }


if __name__ == "__main__":
    sample_input = {
        "destination": "Da Nang",
        "duration_days": 5,
        "traveler_count": 2,
        "budget_level": "medium",
        "travel_style": "standard"
    }
    print(json.dumps(run(sample_input), ensure_ascii=False, indent=2))
