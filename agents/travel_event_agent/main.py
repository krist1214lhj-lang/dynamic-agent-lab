import json
import os
from pathlib import Path
from datetime import datetime, timedelta

try:
    import requests
except ImportError:
    requests = None

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if load_dotenv:
    load_dotenv(PROJECT_ROOT / ".env", override=True)

def run(input_data):
    safe_input = input_data if isinstance(input_data, dict) else {}
    destination = safe_input.get("destination") or "서울"
    days = int(safe_input.get("days", 3))
    
    # 추가 조건 파싱
    companions = safe_input.get("companions", [])
    themes = safe_input.get("themes", [])
    priority = safe_input.get("priority", "")

    # 테마에 따른 키워드 가중치
    theme_keywords = {
        "activity": "체험 액티비티 스포츠",
        "healing": "전시회 정원 산책",
        "foodie": "축제 먹거리 페스티벌",
        "culture": "전통 공연 역사",
    }
    added_keyword = " ".join([theme_keywords.get(t, "") for t in themes]).strip()
    
    summary = f"{destination} {days}일 여정 동안 즐기기 좋은 행사입니다. "
    if "family" in companions: summary += "아이와 함께 안전하고 유익하게 즐길 수 있는 체험 위주로 선정했습니다. "
    if "activity" in themes: summary += "역동적인 활동과 체험 중심의 행사를 추천합니다."

    # Mock 데이터 (조건 반영 시뮬레이션)
    event_items = [
        {
            "name": f"{destination} { '가족 체험' if 'family' in companions else '대표 축제' }",
            "address": f"{destination} 축제장",
            "category": "축제/행사",
            "event_period": "상시",
            "overview_hint": f"{', '.join(themes)} 테마에 맞춘 맞춤형 추천 행사입니다."
        },
        {
            "name": f"{destination} {'인기 핫플레이스' if priority == 'popularity' else '문화 공연'}",
            "address": f"{destination} 시내",
            "category": "공연/전시",
            "event_period": "주말 위주",
            "overview_hint": "가장 만족도가 높은 핵심 이벤트입니다."
        }
    ]

    return {
        "agent": "travel_event_agent",
        "summary": summary,
        "event_items": event_items,
        "recommendations": [
            "방문 전 공식 홈페이지에서 일정을 한 번 더 확인해 주세요.",
            "인기 행사는 사전 예약이 필요할 수 있습니다."
        ],
        "debug_info": { "companions": companions, "themes": themes, "priority": priority }
    }

if __name__ == "__main__":
    print(json.dumps(run({"destination": "제주", "companions": ["family"], "themes": ["activity"]}), ensure_ascii=False, indent=2))
