import json
import os
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv()

def run(input_data):
    destination = input_data.get("destination", "부산")
    days = int(input_data.get("days", 1))
    budget_level = input_data.get("budget_level", "medium")
    
    # 추가 조건 추출
    companions = input_data.get("companions", [])
    themes = input_data.get("themes", [])
    priority = input_data.get("priority", "")
    
    if days == 1:
        return {
            "agent": "travel_lodging_agent",
            "destination": destination,
            "lodging_required": False,
            "summary": "당일치기 일정에는 숙박 추천이 포함되지 않습니다.",
            "lodging_items": [],
            "recommendations": ["당일치기 여행이므로 숙박은 제외합니다."]
        }

    # 추천 로직 (조건 반영)
    recommendations = []
    if "couple" in companions: recommendations.append("커플 여행에 어울리는 분위기 좋은 호텔이나 부티크 숙소를 우선 추천합니다.")
    if "family" in companions: recommendations.append("가족 여행객을 위해 키즈존이나 다인실 이용이 가능한 리조트 위주로 선별했습니다.")
    if "healing" in themes: recommendations.append("휴식을 위해 소음이 적고 자연 경관이 좋은 조용한 숙소를 추천합니다.")
    if priority == "quality": recommendations.append("만족도를 극대화할 수 있는 프리미엄급 숙소입니다.")
    
    if not recommendations:
        recommendations.append(f"{destination} 시내 접근성이 좋은 숙소 위주로 구성했습니다.")

    # Mock 데이터 (조건에 따른 동적 생성)
    lodging_items = [
        {
            "name": f"{destination} 맞춤형 숙소 1",
            "address": f"{destination} 중심지 인근",
            "category": "호텔/리조트",
            "reason": f"{', '.join(companions + themes)} 조건을 고려한 최적의 장소입니다."
        },
        {
            "name": f"{destination} 프리미엄 스테이",
            "address": f"{destination} 관광지 주변",
            "category": "호텔",
            "reason": "평점이 높고 리뷰가 검증된 숙박 후보입니다."
        }
    ]

    return {
        "agent": "travel_lodging_agent",
        "data_source": "mock_plus_conditions",
        "destination": destination,
        "days": days,
        "lodging_items": lodging_items,
        "recommendations": recommendations,
        "summary": f"{destination} {days}일 여정을 위한 맞춤형 숙소 추천입니다.",
        "debug_info": {
            "companions": companions,
            "themes": themes,
            "priority": priority
        }
    }

if __name__ == "__main__":
    print(json.dumps(run({"destination": "부산", "days": 3, "companions": ["couple"], "themes": ["healing"]}), ensure_ascii=False, indent=2))
