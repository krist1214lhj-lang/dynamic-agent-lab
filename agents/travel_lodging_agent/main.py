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

# .env 로드 (로컬 개발 환경용)
if load_dotenv:
    load_dotenv()

def run(input_data):
    """
    숙박시설 추천 에이전트
    - 목적지, 기간, 예산 수준을 기반으로 숙박시설을 추천합니다.
    - TourAPI contentTypeId=32 (숙박) 사용
    - 당일치기(days=1)는 숙박 제외
    """
    destination = input_data.get("destination", "부산")
    days = int(input_data.get("days", 1))
    budget_level = input_data.get("budget_level", "medium")
    
    # 1. 당일치기 처리
    if days == 1:
        return {
            "agent": "travel_lodging_agent",
            "data_source": "rule_based_fallback",
            "destination": destination,
            "days": 1,
            "lodging_required": False,
            "lodging_nights": 0,
            "lodging_items": [],
            "recommendations": [
                "당일치기 여행이므로 숙박시설 추천은 제외합니다.",
                "귀가 교통편 시간을 먼저 확인하세요."
            ],
            "summary": "당일치기 일정에는 숙박이 필요하지 않습니다.",
            "debug_info": {
                "api_provider": "tour_api",
                "env_key_valid": True,
                "fallback_reason": "day_trip_no_lodging_required",
                "service_key_leaked": False
            }
        }

    # 2. TourAPI 설정
    service_key = os.getenv("TOUR_API_SERVICE_KEY")
    env_key_valid = bool(service_key and service_key != "YOUR_TOUR_API_SERVICE_KEY_HERE")
    
    # 지역 코드 매핑 (기본적인 지역들)
    area_code_map = {
        "서울": "1",
        "인천": "2",
        "대전": "3",
        "대구": "4",
        "광주": "5",
        "부산": "6",
        "울산": "7",
        "세종": "8",
        "강릉": "32",
        "속초": "32",
        "춘천": "32",
        "경주": "35",
        "전주": "37",
        "여수": "38",
        "제주": "39"
    }
    
    area_code = area_code_map.get(destination)
    lodging_items = []
    data_source = "mock_fallback"
    fallback_reason = None
    
    # 3. TourAPI 호출 시도
    if env_key_valid and area_code and requests:
        try:
            url = "http://apis.data.go.kr/B551011/KorService1/areaBasedList1"
            params = {
                "serviceKey": service_key,
                "numOfRows": 10,
                "pageNo": 1,
                "MobileOS": "ETC",
                "MobileApp": "TravelAgent",
                "_type": "json",
                "listYN": "Y",
                "arrange": "Q", # 인기순/조회순 가깝게
                "contentTypeId": "32", # 숙박
                "areaCode": area_code
            }
            
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                res_data = response.json()
                items = res_data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
                
                if isinstance(items, dict): # 항목이 하나일 때 dict로 올 수 있음
                    items = [items]
                
                if items:
                    for item in items[:5]: # 최대 5개
                        lodging_items.append({
                            "name": item.get("title"),
                            "address": item.get("addr1"),
                            "category": "숙박",
                            "image": item.get("firstimage") or item.get("firstimage2"),
                            "mapx": item.get("mapx"),
                            "mapy": item.get("mapy"),
                            "tel": item.get("tel"),
                            "reason": f"{destination} {days}일 여행에서 접근성이 좋은 숙박 후보입니다."
                        })
                    data_source = "tour_api"
                else:
                    fallback_reason = "tour_api_no_results"
            else:
                fallback_reason = "tour_api_http_error"
        except Exception as e:
            fallback_reason = f"tour_api_exception: {str(e)}"
    else:
        if not env_key_valid:
            fallback_reason = "missing_tour_api_service_key"
        elif not area_code:
            fallback_reason = "missing_area_code_for_destination"
        elif not requests:
            fallback_reason = "requests_library_missing"

    # 4. Fallback 처리 (API 실패 시)
    if not lodging_items:
        data_source = "mock_fallback" if fallback_reason != "missing_area_code_for_destination" else "rule_based_fallback"
        
        # 기본 Mock 데이터
        mock_lodgings = {
            "low": [
                {"name": f"{destination} 게스트하우스", "address": f"{destination} 시내", "tel": "010-1234-5678", "reason": "합리적인 가격의 숙소입니다."},
                {"name": f"{destination} 비즈니스 호텔", "address": f"{destination} 역 인근", "tel": "051-987-6543", "reason": "교통 접근성이 우수합니다."}
            ],
            "medium": [
                {"name": f"{destination} 부티크 호텔", "address": f"{destination} 중심가", "tel": "051-123-4567", "reason": "깔끔하고 위치가 좋은 숙소입니다."},
                {"name": f"{destination} 가족형 콘도", "address": f"{destination} 관광지 주변", "tel": "051-555-6666", "reason": "가족 여행객에게 적합합니다."}
            ],
            "high": [
                {"name": f"{destination} 그랜드 리조트", "address": f"{destination} 해변가", "tel": "051-000-0000", "reason": "최고급 시설과 전망을 자랑합니다."},
                {"name": f"{destination} 프리미엄 호텔", "address": f"{destination} 도심 야경 명소", "tel": "051-777-8888", "reason": "이동 편의성과 서비스가 뛰어납니다."}
            ]
        }
        
        for mock in mock_lodgings.get(budget_level, mock_lodgings["medium"]):
            lodging_items.append({
                "name": mock["name"],
                "address": mock["address"],
                "category": "숙박",
                "image": None,
                "tel": mock["tel"],
                "reason": mock["reason"]
            })

    # 5. 추천 문구 조정 (budget_level 기준)
    recommendations = []
    if budget_level == "low":
        recommendations = [
            "게스트하우스나 비즈니스 호텔 등 가성비 좋은 숙소 위주로 구성하세요.",
            "숙박비를 절약하고 대중교통 접근성이 좋은 곳을 우선 추천합니다."
        ]
    elif budget_level == "high":
        recommendations = [
            "관광지 인근의 고급 호텔이나 리조트에서 편안한 휴식을 즐기세요.",
            "이동 편의성과 숙박 만족도를 최우선으로 고려한 추천입니다."
        ]
    else:
        recommendations = [
            "위치와 가격 균형이 좋은 호텔 및 가족형 숙소를 추천합니다.",
            "주요 관광지 동선을 고려하여 선정되었습니다."
        ]

    return {
        "agent": "travel_lodging_agent",
        "data_source": data_source,
        "destination": destination,
        "days": days,
        "lodging_required": True,
        "lodging_nights": days - 1,
        "lodging_items": lodging_items,
        "recommendations": recommendations,
        "summary": f"{destination}에서의 {days-1}박 일정을 위한 숙박 시설 추천입니다.",
        "debug_info": {
            "api_provider": "tour_api",
            "env_key_valid": env_key_valid,
            "env_key_length": len(service_key) if service_key else 0,
            "fallback_reason": fallback_reason,
            "service_key_leaked": False
        }
    }

if __name__ == "__main__":
    sample_input = {
        "destination": "부산",
        "days": 3,
        "budget_level": "medium"
    }
    print(json.dumps(run(sample_input), ensure_ascii=False, indent=2))
