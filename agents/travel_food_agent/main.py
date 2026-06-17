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

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if load_dotenv:
    load_dotenv(PROJECT_ROOT / ".env", override=True)

MOCK_FOOD_ITEMS = {
    "제주": [
        {"name": "키즈존 흑돼지 식당", "address": "제주 제주시", "category": "가족친화", "menu_hint": "흑돼지", "meal_time": "저녁"},
        {"name": "오션뷰 카페", "address": "제주 서귀포시", "category": "인기명소", "menu_hint": "디저트", "meal_time": "간식"},
        {"name": "고기국수 로컬맛집", "address": "제주 제주시", "category": "한식", "menu_hint": "고기국수", "meal_time": "점심"},
    ],
    "부산": [
        {"name": "해운대 줄서는 국밥집", "address": "부산 해운대구", "category": "인기명소", "menu_hint": "돼지국밥", "meal_time": "아침/점심"},
        {"name": "광안리 가족 횟집", "address": "부산 수영구", "category": "가족친화", "menu_hint": "모듬회", "meal_time": "저녁"},
        {"name": "남포동 씨앗호떡", "address": "부산 중구", "category": "길거리음식", "menu_hint": "호떡", "meal_time": "간식"},
    ],
    "서울": [
        {"name": "삼청동 한정식", "address": "서울 종로구", "category": "가족친화", "menu_hint": "한정식", "meal_time": "점심/저녁"},
        {"name": "성수동 핫플 카페", "address": "서울 성동구", "category": "인기명소", "menu_hint": "브런치", "meal_time": "점심"},
        {"name": "명동 교자", "address": "서울 중구", "category": "인기명소", "menu_hint": "칼국수", "meal_time": "점심/저녁"},
    ]
}

def run(input_data):
    safe_input = input_data if isinstance(input_data, dict) else {}
    destination = safe_input.get("destination") or "서울"
    
    # 추가 조건 파싱
    companions = safe_input.get("companions", [])
    themes = safe_input.get("themes", [])
    priority = safe_input.get("priority", "")
    
    # 추천 로직 보강
    summary = f"{destination} 지역의 엄선된 맛집 리스트입니다. "
    if "family" in companions:
        summary += "아이와 함께 편안하게 식사할 수 있는 키즈존 및 깔끔한 환경의 식당을 우선했습니다. "
    if priority == "popularity":
        summary += "줄을 서더라도 만족도가 높은 소문난 핫플레이스 위주로 구성했습니다."
    elif priority == "cost":
        summary += "가성비 좋은 현지인 맛집을 중심으로 선별했습니다."

    # 데이터 선별 (가짜 필터링)
    base_items = MOCK_FOOD_ITEMS.get(destination, MOCK_FOOD_ITEMS["서울"])
    food_items = []
    
    # 조건에 따른 정렬/필터링 시뮬레이션
    if "family" in companions:
        food_items.extend([i for i in base_items if i["category"] == "가족친화"])
    if priority == "popularity":
        food_items.extend([i for i in base_items if i["category"] == "인기명소"])
    
    if not food_items: food_items = base_items

    return {
        "agent": "travel_food_agent",
        "summary": summary,
        "food_items": food_items[:6],
        "recommendations": [
            "인기 맛집은 방문 전 캐치테이블 등으로 원격 웨이팅을 확인하세요.",
            "아이 동반 시 아기 의자 유무를 미리 전화로 체크하시면 좋습니다."
        ],
        "debug_info": { "companions": companions, "themes": themes, "priority": priority }
    }

if __name__ == "__main__":
    print(json.dumps(run({"destination": "제주", "companions": ["family"], "priority": "popularity"}), ensure_ascii=False, indent=2))
