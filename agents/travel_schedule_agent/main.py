import json


def run(input_data):
    """Return a mock travel itinerary without calling AI APIs."""
    destination = input_data.get("destination", "추천 여행지")
    days = int(input_data.get("days", input_data.get("duration_days", 3)))
    travel_style = input_data.get("travel_style", "relaxed")
    budget_level = input_data.get("budget_level", "medium")

    itinerary = []
    templates = [
        {
            "title": "도착 및 핵심 지역 둘러보기",
            "morning": "이동 후 숙소에 짐을 맡기고 주변 교통 동선을 확인합니다.",
            "afternoon": "대표 명소 한 곳과 가까운 산책 코스를 가볍게 둘러봅니다.",
            "evening": "현지 식당에서 저녁 식사를 하고 야경 명소를 방문합니다."
        },
        {
            "title": "주요 명소 집중 일정",
            "morning": "인기 명소를 이른 시간에 방문해 혼잡을 피합니다.",
            "afternoon": "박물관, 시장, 해변 등 관심사에 맞는 코스를 선택합니다.",
            "evening": "로컬 맛집 또는 야시장 중심으로 식사 일정을 잡습니다."
        },
        {
            "title": "여유로운 마무리 및 귀가",
            "morning": "카페나 공원에서 여유롭게 시간을 보내며 체크아웃을 준비합니다.",
            "afternoon": "기념품 구매 후 공항이나 역으로 이동합니다.",
            "evening": "귀가 일정에 맞춰 이동하고 여행을 마무리합니다."
        }
    ]

    for index in range(days):
        template = templates[min(index, len(templates) - 1)]
        itinerary.append({
            "day": index + 1,
            "title": template["title"],
            "morning": template["morning"],
            "afternoon": template["afternoon"],
            "evening": template["evening"]
        })

    return {
        "agent": "travel_schedule_agent",
        "summary": (
            f"Mock {days}-day itinerary for {destination}, using travel style "
            f"'{travel_style}' and budget level '{budget_level}'."
        ),
        "itinerary": itinerary,
        "schedule_tips": [
            "첫날은 이동 피로를 고려해 핵심 지역 위주로 짧게 구성하는 것이 좋습니다.",
            "인기 명소는 오전 시간대에 배치하면 대기 시간을 줄일 수 있습니다.",
            "마지막 날은 이동 시간을 넉넉히 확보해 일정 지연 위험을 낮춥니다."
        ],
        "risks": [
            "날씨에 따라 야외 일정이 변경될 수 있습니다.",
            "성수기에는 주요 명소와 식당 예약이 필요할 수 있습니다.",
            "교통 지연이 발생하면 오후 일정이 밀릴 수 있습니다."
        ],
        "next_agents": [
            "travel_budget_agent",
            "hotel_recommendation_agent",
            "transportation_agent"
        ]
    }


if __name__ == "__main__":
    sample_input = {
        "user_request": "서울에서 2박 3일로 저렴하게 갈 수 있는 여행 일정을 알려줘.",
        "destination": "Da Nang",
        "days": 3,
        "travel_style": "relaxed",
        "budget_level": "low"
    }
    print(json.dumps(run(sample_input), ensure_ascii=False, indent=2))
