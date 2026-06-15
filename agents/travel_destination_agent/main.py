import json
import os

try:
    import requests
except ImportError:  # pragma: no cover - dependency fallback
    requests = None


TOUR_API_BASE_URL = "https://apis.data.go.kr/B551011/KorService2"
TOUR_API_MOBILE_OS = "ETC"
TOUR_API_MOBILE_APP = "dynamic-agent-lab"
TOUR_ATTRACTION_CONTENT_TYPE_ID = "12"
MAX_DESTINATION_ITEMS = 5

AREA_CODE_BY_NAME = {
    "서울": "1",
    "인천": "2",
    "대전": "3",
    "대구": "4",
    "광주": "5",
    "부산": "6",
    "강릉": "32",
    "제주": "39",
}

PLACEHOLDER_KEYS = {
    "",
    "your_tour_api_service_key_here",
    "YOUR_TOUR_API_SERVICE_KEY",
    "TOUR_API_SERVICE_KEY",
}


def _safe_input(input_data):
    return input_data if isinstance(input_data, dict) else {}


def _trip_context(input_data):
    safe_input = _safe_input(input_data)
    destination = safe_input.get("destination") or safe_input.get("location") or ""
    try:
        days = int(safe_input.get("days", safe_input.get("duration_days", 3)))
    except (TypeError, ValueError):
        days = 3
    budget_level = (
        safe_input.get("budget_level")
        or safe_input.get("budget")
        or "medium"
    )
    user_request = str(safe_input.get("user_request") or "").strip()
    destination_type = safe_input.get("destination_type", "general")
    season = safe_input.get("season", "any")
    traveler_count = safe_input.get("traveler_count", 1)
    return {
        "safe_input": safe_input,
        "destination": destination,
        "days": days,
        "budget_level": budget_level,
        "user_request": user_request,
        "destination_type": destination_type,
        "season": season,
        "traveler_count": traveler_count,
    }


def _tour_api_key():
    return os.getenv("TOUR_API_SERVICE_KEY") or ""


def _is_valid_service_key(service_key):
    return bool(service_key) and service_key not in PLACEHOLDER_KEYS


def _debug_info(service_key="", fallback_reason=None):
    return {
        "env_key_valid": _is_valid_service_key(service_key),
        "env_key_length": len(service_key or ""),
        "api_provider": "tour_api",
        "fallback_reason": fallback_reason,
        "service_key_leaked": False,
    }


def _detect_area_code(destination, user_request):
    for value in [destination, user_request]:
        text = str(value or "")
        for area_name, area_code in AREA_CODE_BY_NAME.items():
            if area_name and area_name in text:
                return area_name, area_code
    return None, None


def _keyword_from_request(user_request):
    text = str(user_request or "").strip()
    if text:
        for area_name in AREA_CODE_BY_NAME:
            text = text.replace(area_name, " ")
        keywords = [
            word.strip(" ,./!?()[]{}'\"")
            for word in text.split()
            if len(word.strip(" ,./!?()[]{}'\"")) >= 2
        ]
        if keywords:
            return keywords[0]
    return ""


def _tour_api_params(service_key):
    return {
        "serviceKey": service_key,
        "MobileOS": TOUR_API_MOBILE_OS,
        "MobileApp": TOUR_API_MOBILE_APP,
        "_type": "json",
        "numOfRows": 12,
        "pageNo": 1,
    }


def _response_items(payload):
    response = payload.get("response") if isinstance(payload, dict) else None
    if not isinstance(response, dict):
        raise ValueError("missing_response")

    header = response.get("header") if isinstance(response.get("header"), dict) else {}
    result_code = str(header.get("resultCode") or "")
    if result_code and result_code != "0000":
        raise RuntimeError("tour_api_response_error")

    body = response.get("body") if isinstance(response.get("body"), dict) else {}
    items = body.get("items")
    if isinstance(items, dict):
        item_list = items.get("item")
    else:
        item_list = items

    if isinstance(item_list, dict):
        return [item_list]
    if isinstance(item_list, list):
        return [item for item in item_list if isinstance(item, dict)]
    return []


def _fetch_area_based_items(service_key, area_code):
    params = _tour_api_params(service_key)
    params.update(
        {
            "areaCode": area_code,
            "contentTypeId": TOUR_ATTRACTION_CONTENT_TYPE_ID,
            "arrange": "P",
        }
    )
    response = requests.get(
        f"{TOUR_API_BASE_URL}/areaBasedList2",
        params=params,
        timeout=6,
    )
    if response.status_code >= 400:
        raise RuntimeError("tour_api_http_error")
    try:
        return _response_items(response.json())
    except RuntimeError:
        raise
    except ValueError as exc:
        raise ValueError("tour_api_parse_error") from exc


def _fetch_keyword_items(service_key, keyword):
    params = _tour_api_params(service_key)
    params.update(
        {
            "keyword": keyword,
            "contentTypeId": TOUR_ATTRACTION_CONTENT_TYPE_ID,
            "arrange": "P",
        }
    )
    response = requests.get(
        f"{TOUR_API_BASE_URL}/searchKeyword2",
        params=params,
        timeout=6,
    )
    if response.status_code >= 400:
        raise RuntimeError("tour_api_http_error")
    try:
        return _response_items(response.json())
    except RuntimeError:
        raise
    except ValueError as exc:
        raise ValueError("tour_api_parse_error") from exc


def _category_label(item):
    content_type_id = str(item.get("contenttypeid") or "")
    if content_type_id == "12":
        return "관광지"
    if content_type_id == "14":
        return "문화시설"
    if content_type_id == "28":
        return "레포츠"
    return "여행지"


def _to_recommendation(item, destination):
    name = str(item.get("title") or "").strip() or "추천 여행지"
    address = str(item.get("addr1") or item.get("addr2") or "").strip()
    return {
        "name": name,
        "category": _category_label(item),
        "address": address,
        "mapx": str(item.get("mapx") or ""),
        "mapy": str(item.get("mapy") or ""),
        "image": str(item.get("firstimage") or item.get("firstimage2") or ""),
        "reason": f"{destination or '선택한 지역'} 여행에서 함께 검토할 만한 TourAPI 추천 여행지입니다.",
    }


def _build_tour_api_result(destination, recommendations, service_key):
    return {
        "agent": "travel_destination_agent",
        "data_source": "tour_api",
        "destination": destination,
        "summary": f"{destination or '선택한 지역'} 기준 TourAPI 추천 여행지를 정리했습니다.",
        "recommendations": recommendations,
        "reasons": [
            "TourAPI 지역/키워드 검색 결과에서 여행지 후보를 추출했습니다.",
            "주소, 좌표, 대표 이미지처럼 일정 구성에 필요한 핵심 정보만 정리했습니다.",
            "실제 운영 시간과 상세 정보는 방문 전 공식 안내를 확인하세요.",
        ],
        "next_agents": [
            "travel_schedule_agent",
            "travel_tour_agent",
            "travel_transport_agent",
        ],
        "debug_info": _debug_info(service_key, None),
    }


def call_tour_api_destination(input_data):
    context = _trip_context(input_data)
    destination = context["destination"]
    user_request = context["user_request"]
    service_key = _tour_api_key()

    if not _is_valid_service_key(service_key):
        return None, "missing_tour_api_service_key", service_key
    if requests is None:
        return None, "missing_requests_dependency", service_key

    area_name, area_code = _detect_area_code(destination, user_request)
    keyword = _keyword_from_request(user_request)

    try:
        if area_code:
            raw_items = _fetch_area_based_items(service_key, area_code)
            result_destination = area_name or destination
        elif keyword:
            raw_items = _fetch_keyword_items(service_key, keyword)
            result_destination = destination or keyword
        else:
            return None, "missing_area_code_for_destination", service_key
    except RuntimeError as exc:
        reason = str(exc) or "tour_api_response_error"
        if reason not in {"tour_api_http_error", "tour_api_response_error"}:
            reason = "tour_api_response_error"
        return None, reason, service_key
    except ValueError:
        return None, "tour_api_parse_error", service_key
    except requests.exceptions.RequestException:
        return None, "tour_api_request_exception", service_key
    except Exception:
        return None, "tour_api_parse_error", service_key

    recommendations = [
        _to_recommendation(item, result_destination)
        for item in raw_items
        if item.get("title")
    ][:MAX_DESTINATION_ITEMS]
    if not recommendations:
        return None, "tour_api_no_results", service_key

    return _build_tour_api_result(result_destination, recommendations, service_key), None, service_key


def _fallback_recommendations(context):
    destination = context["destination"] or "국내"
    budget = context["budget_level"]
    days = context["days"]
    return [
        {
            "name": f"{destination} 대표 명소",
            "country": "South Korea",
            "type": "city" if destination in {"서울", "부산", "대전", "대구", "광주", "인천"} else "nature",
            "estimated_budget": budget,
            "recommended_days": min(max(days, 2), 5),
            "highlights": ["대표 관광지", "지역 산책 코스", "현지 식사"],
        },
        {
            "name": f"{destination} 로컬 코스",
            "country": "South Korea",
            "type": "culture",
            "estimated_budget": budget,
            "recommended_days": min(max(days, 2), 4),
            "highlights": ["시장", "카페 거리", "문화 공간"],
        },
        {
            "name": f"{destination} 여유 일정",
            "country": "South Korea",
            "type": "relax",
            "estimated_budget": budget,
            "recommended_days": min(max(days, 1), 3),
            "highlights": ["전망 좋은 장소", "가벼운 산책", "휴식"],
        },
    ]


def build_mock_destination_result(input_data, fallback_reason):
    context = _trip_context(input_data)
    service_key = _tour_api_key()
    recommendations = _fallback_recommendations(context)
    return {
        "agent": "travel_destination_agent",
        "data_source": "mock_fallback",
        "destination": context["destination"],
        "summary": (
            f"{context['destination'] or '선택한 지역'} 여행지 추천을 mock_fallback으로 구성했습니다. "
            f"예산 수준 '{context['budget_level']}', {context['days']}일 일정 기준입니다."
        ),
        "recommendations": recommendations,
        "reasons": [
            "TourAPI 키가 없거나 호출에 실패해 기존 mock_fallback 후보를 사용했습니다.",
            "입력된 목적지, 기간, 예산을 기준으로 안정적인 기본 추천 구조를 유지했습니다.",
            f"fallback_reason={fallback_reason}",
        ],
        "next_agents": [
            "travel_schedule_agent",
            "travel_tour_agent",
            "travel_transport_agent",
        ],
        "debug_info": _debug_info(service_key, fallback_reason),
    }


def run(input_data):
    """Return TourAPI destination recommendations with safe mock fallback."""
    tour_api_result, fallback_reason, _service_key = call_tour_api_destination(input_data)
    if tour_api_result:
        return tour_api_result
    return build_mock_destination_result(
        input_data,
        fallback_reason or "tour_api_response_error",
    )


if __name__ == "__main__":
    sample_input = {
        "destination": "부산",
        "location": "부산",
        "origin": "서울",
        "days": 3,
        "budget_level": "medium",
        "requested_features": ["destination"],
    }
    print(json.dumps(run(sample_input), ensure_ascii=False, indent=2))
