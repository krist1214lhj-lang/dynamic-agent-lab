import json
import os
from pathlib import Path

try:
    import requests
except ImportError:  # pragma: no cover - environment fallback
    requests = None

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - environment fallback
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if load_dotenv is not None:
    load_dotenv(PROJECT_ROOT / ".env", override=True)

TOUR_API_BASE_URL = "https://apis.data.go.kr/B551011/KorService2"
TOUR_API_MOBILE_OS = "ETC"
TOUR_API_MOBILE_APP = "dynamic-agent-lab"
EVENT_CONTENT_TYPE_ID = "15"
MAX_EVENT_ITEMS = 6

PLACEHOLDER_SERVICE_KEYS = {
    "",
    "your_tour_api_service_key_here",
    "YOUR_TOUR_API_SERVICE_KEY",
    "TOUR_API_SERVICE_KEY",
    "실제_관광공사_서비스키",
}

AREA_CODE_BY_NAME = {
    "서울": "1",
    "인천": "2",
    "대전": "3",
    "대구": "4",
    "광주": "5",
    "부산": "6",
    "울산": "7",
    "세종": "8",
    "경기": "31",
    "강원": "32",
    "충북": "33",
    "충남": "34",
    "경북": "35",
    "경남": "36",
    "전북": "37",
    "전남": "38",
    "제주": "39",
}

REGION_PRIORITY = [
    "서울",
    "부산",
    "제주",
    "강릉",
    "속초",
    "춘천",
    "전주",
    "여수",
    "경주",
    "인천",
    "대전",
    "대구",
    "광주",
    "울산",
    "세종",
    "경기",
    "강원",
    "충북",
    "충남",
    "경북",
    "경남",
    "전북",
    "전남",
]

EVENT_SEARCH_KEYWORDS = [
    "{destination} 축제",
    "{destination} 행사",
    "{destination} 문화행사",
    "{destination} 공연",
    "{destination} 페스티벌",
]

MOCK_EVENT_ITEMS = {
    "제주": [
        {
            "name": "제주 해녀문화 행사",
            "address": "제주특별자치도 제주시",
            "category": "문화행사",
            "event_period": "상시 또는 시즌별",
            "image": "",
            "mapx": "126.531",
            "mapy": "33.499",
            "tel": "정보 없음",
            "overview_hint": "제주 해녀 문화를 주제로 한 체험형 문화행사입니다.",
        },
        {
            "name": "제주 들불축제",
            "address": "제주특별자치도 제주시 애월읍",
            "category": "축제",
            "event_period": "시즌별",
            "image": "",
            "mapx": "126.410",
            "mapy": "33.393",
            "tel": "정보 없음",
            "overview_hint": "제주의 대표적인 봄철 축제 후보입니다.",
        },
        {
            "name": "서귀포 문화행사",
            "address": "제주특별자치도 서귀포시",
            "category": "문화행사",
            "event_period": "수시",
            "image": "",
            "mapx": "126.560",
            "mapy": "33.250",
            "tel": "정보 없음",
            "overview_hint": "서귀포 도심과 해안 동선에 맞춰 확인하기 좋은 행사입니다.",
        },
        {
            "name": "해변 공연",
            "address": "제주특별자치도 해안가 일대",
            "category": "공연",
            "event_period": "주말/시즌별",
            "image": "",
            "mapx": "126.500",
            "mapy": "33.450",
            "tel": "정보 없음",
            "overview_hint": "해변 산책 일정과 함께 확인하기 좋은 공연 후보입니다.",
        },
    ],
    "부산": [
        {
            "name": "부산바다축제",
            "address": "부산광역시 해운대구 일대",
            "category": "축제",
            "event_period": "여름 시즌",
            "image": "",
            "mapx": "129.160",
            "mapy": "35.158",
            "tel": "정보 없음",
            "overview_hint": "해운대와 광안리 동선에 맞는 대표 여름 축제입니다.",
        },
        {
            "name": "부산불꽃축제",
            "address": "부산광역시 수영구 광안리해변",
            "category": "축제",
            "event_period": "가을 시즌",
            "image": "",
            "mapx": "129.118",
            "mapy": "35.153",
            "tel": "정보 없음",
            "overview_hint": "광안대교 야경과 함께 즐기는 대표 행사입니다.",
        },
        {
            "name": "영화의전당 행사",
            "address": "부산광역시 해운대구",
            "category": "문화행사",
            "event_period": "수시",
            "image": "",
            "mapx": "129.127",
            "mapy": "35.171",
            "tel": "정보 없음",
            "overview_hint": "영화와 공연 중심의 실내외 문화행사 후보입니다.",
        },
    ],
    "전주": [
        {
            "name": "전주한지문화축제",
            "address": "전북특별자치도 전주시",
            "category": "축제",
            "event_period": "시즌별",
            "image": "",
            "mapx": "127.147",
            "mapy": "35.819",
            "tel": "정보 없음",
            "overview_hint": "전주의 전통문화와 한지를 주제로 한 축제입니다.",
        },
        {
            "name": "전주대사습놀이",
            "address": "전북특별자치도 전주시",
            "category": "전통공연",
            "event_period": "시즌별",
            "image": "",
            "mapx": "127.150",
            "mapy": "35.815",
            "tel": "정보 없음",
            "overview_hint": "국악과 전통공연을 중심으로 한 대표 행사입니다.",
        },
        {
            "name": "한옥마을 문화행사",
            "address": "전북특별자치도 전주시 완산구",
            "category": "문화행사",
            "event_period": "수시",
            "image": "",
            "mapx": "127.153",
            "mapy": "35.815",
            "tel": "정보 없음",
            "overview_hint": "한옥마을 관광 동선과 함께 확인하기 좋은 행사입니다.",
        },
    ],
    "강릉": [
        {
            "name": "강릉단오제",
            "address": "강원특별자치도 강릉시",
            "category": "전통축제",
            "event_period": "시즌별",
            "image": "",
            "mapx": "128.896",
            "mapy": "37.752",
            "tel": "정보 없음",
            "overview_hint": "강릉의 대표 전통문화 축제입니다.",
        },
        {
            "name": "커피축제",
            "address": "강원특별자치도 강릉시",
            "category": "축제",
            "event_period": "가을 시즌",
            "image": "",
            "mapx": "128.948",
            "mapy": "37.769",
            "tel": "정보 없음",
            "overview_hint": "카페거리와 함께 묶기 좋은 커피 테마 행사입니다.",
        },
        {
            "name": "경포해변 행사",
            "address": "강원특별자치도 강릉시 경포해변",
            "category": "해변행사",
            "event_period": "여름/주말",
            "image": "",
            "mapx": "128.909",
            "mapy": "37.805",
            "tel": "정보 없음",
            "overview_hint": "해변 산책과 함께 확인하기 좋은 야외 행사입니다.",
        },
    ],
    "여수": [
        {
            "name": "여수밤바다 버스킹",
            "address": "전라남도 여수시 해안가",
            "category": "공연",
            "event_period": "저녁/주말",
            "image": "",
            "mapx": "127.738",
            "mapy": "34.747",
            "tel": "정보 없음",
            "overview_hint": "밤바다 산책 동선과 잘 맞는 공연 후보입니다.",
        },
        {
            "name": "거북선축제",
            "address": "전라남도 여수시",
            "category": "축제",
            "event_period": "시즌별",
            "image": "",
            "mapx": "127.662",
            "mapy": "34.760",
            "tel": "정보 없음",
            "overview_hint": "여수의 역사와 해양문화를 함께 다루는 축제입니다.",
        },
        {
            "name": "해양문화행사",
            "address": "전라남도 여수시 일대",
            "category": "문화행사",
            "event_period": "수시",
            "image": "",
            "mapx": "127.730",
            "mapy": "34.740",
            "tel": "정보 없음",
            "overview_hint": "해양 관광지와 함께 확인하기 좋은 행사입니다.",
        },
    ],
    "서울": [
        {
            "name": "궁중문화축전",
            "address": "서울특별시 종로구 고궁 일대",
            "category": "문화축제",
            "event_period": "봄/가을 시즌",
            "image": "",
            "mapx": "126.976",
            "mapy": "37.579",
            "tel": "정보 없음",
            "overview_hint": "고궁 방문 일정과 함께 확인하기 좋은 대표 문화행사입니다.",
        },
        {
            "name": "한강축제",
            "address": "서울특별시 한강공원 일대",
            "category": "축제",
            "event_period": "여름 시즌",
            "image": "",
            "mapx": "126.934",
            "mapy": "37.528",
            "tel": "정보 없음",
            "overview_hint": "한강공원 일정과 함께 묶기 좋은 야외 행사입니다.",
        },
        {
            "name": "서울거리공연",
            "address": "서울특별시 도심 일대",
            "category": "공연",
            "event_period": "수시",
            "image": "",
            "mapx": "126.978",
            "mapy": "37.566",
            "tel": "정보 없음",
            "overview_hint": "도심 이동 중 확인하기 좋은 거리공연 후보입니다.",
        },
        {
            "name": "전시/공연",
            "address": "서울특별시 주요 문화시설",
            "category": "전시공연",
            "event_period": "상시",
            "image": "",
            "mapx": "126.982",
            "mapy": "37.565",
            "tel": "정보 없음",
            "overview_hint": "비 오는 날이나 실내 일정에 넣기 좋은 문화 이벤트입니다.",
        },
    ],
}


def _safe_dict(value):
    return value if isinstance(value, dict) else {}


def _safe_int(value, default=3):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _detect_destination_from_text(text):
    search_text = str(text or "")
    for region in REGION_PRIORITY:
        if region in search_text:
            return region
    return None


def _get_context(input_data):
    safe_input = _safe_dict(input_data)
    user_request = str(safe_input.get("user_request") or "")
    destination = (
        safe_input.get("destination")
        or safe_input.get("location")
        or _detect_destination_from_text(user_request)
        or "서울"
    )
    days = _safe_int(safe_input.get("days", safe_input.get("duration_days", 3)), 3)
    return safe_input, str(destination), days, user_request


def _detect_area_code(input_data):
    safe_input, destination, _days, user_request = _get_context(input_data)
    aliases = {
        "강릉": "32",
        "속초": "32",
        "춘천": "32",
        "전주": "37",
        "여수": "38",
        "경주": "35",
    }
    for candidate in (
        safe_input.get("destination"),
        safe_input.get("location"),
        _detect_destination_from_text(user_request),
        destination,
    ):
        if not candidate:
            continue
        candidate = str(candidate)
        if candidate in AREA_CODE_BY_NAME:
            return candidate, AREA_CODE_BY_NAME[candidate]
        for alias, area_code in aliases.items():
            if alias in candidate:
                return alias, area_code
    return "서울", AREA_CODE_BY_NAME["서울"]


def load_service_key():
    if load_dotenv is not None:
        load_dotenv(PROJECT_ROOT / ".env", override=True)
    return os.getenv("TOUR_API_SERVICE_KEY", "").strip()


def _is_valid_service_key(service_key):
    return str(service_key or "").strip() not in PLACEHOLDER_SERVICE_KEYS


def _safe_error(exc, api_method):
    if hasattr(exc, "response") and getattr(exc.response, "status_code", None):
        status_code = getattr(exc.response, "status_code", None)
        reason = getattr(exc.response, "reason", "") or "HTTP error"
        return f"HTTPError: {status_code} {reason} during {api_method}"
    if isinstance(exc, RuntimeError):
        return f"RuntimeError during {api_method}: {str(exc).splitlines()[0]}"
    return f"{type(exc).__name__} during {api_method}"


def _base_params(service_key):
    return {
        "serviceKey": service_key,
        "MobileOS": TOUR_API_MOBILE_OS,
        "MobileApp": TOUR_API_MOBILE_APP,
        "_type": "json",
        "numOfRows": 12,
        "pageNo": 1,
    }


def _normalize_items(items):
    if isinstance(items, list):
        return [item for item in items if isinstance(item, dict)]
    if isinstance(items, dict):
        return [items]
    return []


def _extract_raw_items(payload):
    if not isinstance(payload, dict):
        return []
    response = payload.get("response", {})
    if not isinstance(response, dict):
        return []
    header = response.get("header", {})
    result_code = str(header.get("resultCode", ""))
    if result_code not in {"0000", "00"}:
        result_msg = header.get("resultMsg", "unknown")
        raise RuntimeError(f"tour_api_result_error: {result_code} {result_msg}")
    body = response.get("body", {})
    if not isinstance(body, dict):
        return []
    items = body.get("items", {})
    if not isinstance(items, dict):
        return []
    return _normalize_items(items.get("item", []))


def _item_address(item):
    address = " ".join(str(item.get(key) or "").strip() for key in ("addr1", "addr2")).strip()
    return address or "주소 정보 없음"


def _item_image(item):
    return str(item.get("firstimage") or item.get("firstimage2") or "")


def _item_period(item):
    start = str(item.get("eventstartdate") or "").strip()
    end = str(item.get("eventenddate") or "").strip()
    if start and end:
        return f"{start}~{end}"
    return start or end or "기간 정보 없음"


def _to_event_item(item):
    return {
        "name": str(item.get("title") or "제목 없음"),
        "address": _item_address(item),
        "category": str(item.get("cat3") or item.get("cat2") or item.get("cat1") or "행사"),
        "event_period": _item_period(item),
        "image": _item_image(item),
        "mapx": str(item.get("mapx") or ""),
        "mapy": str(item.get("mapy") or ""),
        "tel": str(item.get("tel") or "정보 없음"),
        "overview_hint": str(item.get("overview") or item.get("title") or "상세 정보는 방문 전 확인이 필요합니다."),
    }


def _base_event_items(destination):
    if destination in MOCK_EVENT_ITEMS:
        return [dict(item) for item in MOCK_EVENT_ITEMS[destination]]
    return [dict(item) for item in MOCK_EVENT_ITEMS["서울"]]


def _recommendations(destination):
    return [
        f"{destination} 행사 일정은 방문 전 공식 채널에서 날짜와 운영 여부를 확인하세요.",
        "야외 축제는 날씨와 교통 통제 여부를 함께 확인하는 것이 좋습니다.",
        "공연과 전시는 예약 필요 여부를 먼저 확인하세요.",
    ]


def _build_debug_info(
    service_key,
    destination,
    area_code,
    api_method_used,
    data_source,
    fallback_reason=None,
    last_error=None,
    area_based_status_code=None,
    area_based_raw_count=0,
    supplemental_search_used=False,
    supplemental_success_count=0,
):
    env_key_valid = _is_valid_service_key(service_key)
    return {
        "destination": destination,
        "area_code": area_code,
        "content_type_id": 15,
        "api_method_used": api_method_used,
        "data_source": data_source,
        "env_key_present": env_key_valid,
        "env_key_valid": env_key_valid,
        "env_key_length": len(service_key or ""),
        "api_base_url": "KorService2",
        "area_based_status_code": area_based_status_code,
        "area_based_raw_count": area_based_raw_count,
        "supplemental_search_used": supplemental_search_used,
        "supplemental_success_count": supplemental_success_count,
        "fallback_reason": fallback_reason,
        "last_error": last_error,
    }


def _mock_event_result(destination, days, service_key, area_code, reason, last_error=None):
    return {
        "agent": "travel_event_agent",
        "summary": f"Mock event suggestions for {destination} during a {days}일 여행.",
        "destination": destination,
        "data_source": "mock_fallback",
        "event_items": _base_event_items(destination),
        "event_findings": [
            f"{destination} 기준 축제/문화행사 후보를 mock 데이터로 구성했습니다.",
            "실제 운영 기간과 예약 가능 여부는 방문 전 확인이 필요합니다.",
            f"fallback_reason={reason}",
        ],
        "recommendations": _recommendations(destination),
        "debug_info": _build_debug_info(
            service_key,
            destination,
            area_code,
            "mock_fallback",
            "mock_fallback",
            reason,
            last_error or reason,
        ),
    }


def _fetch_area_based_raw_items(service_key, area_code):
    params = _base_params(service_key)
    params["areaCode"] = area_code
    params["contentTypeId"] = EVENT_CONTENT_TYPE_ID
    params["arrange"] = "P"
    response = requests.get(f"{TOUR_API_BASE_URL}/areaBasedList2", params=params, timeout=6)
    response.raise_for_status()
    try:
        payload = response.json()
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"area_based_json_parse_error: {response.status_code}: {exc}") from exc
    return response.status_code, _extract_raw_items(payload)


def _fetch_keyword_raw_items(service_key, keyword, area_code):
    params = _base_params(service_key)
    params["keyword"] = keyword
    params["areaCode"] = area_code
    params["contentTypeId"] = EVENT_CONTENT_TYPE_ID
    params["arrange"] = "P"
    response = requests.get(f"{TOUR_API_BASE_URL}/searchKeyword2", params=params, timeout=6)
    response.raise_for_status()
    try:
        payload = response.json()
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"keyword_json_parse_error: {response.status_code}: {exc}") from exc
    return response.status_code, _extract_raw_items(payload)


def _candidate_keywords(destination):
    return [keyword.format(destination=destination) for keyword in EVENT_SEARCH_KEYWORDS]


def _unique_items(items):
    seen = set()
    unique = []
    for item in items:
        key = str(item.get("contentid") or item.get("title") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _pick_event_items(raw_items):
    picked = [item for item in raw_items if isinstance(item, dict) and str(item.get("title") or "")]
    picked = _unique_items(picked)
    picked.sort(key=lambda item: (1 if _item_image(item) else 0, 1 if _item_address(item) != "주소 정보 없음" else 0), reverse=True)
    return picked[:MAX_EVENT_ITEMS]


def _tour_api_result(destination, days, service_key, area_code, api_method_used, raw_items, area_status=None, area_count=0, supplemental_used=False, supplemental_count=0):
    return {
        "agent": "travel_event_agent",
        "summary": f"TourAPI event results for {destination} during a {days}일 여행.",
        "destination": destination,
        "data_source": "tour_api",
        "event_items": [_to_event_item(item) for item in _pick_event_items(raw_items)],
        "event_findings": [
            f"지역코드(areaCode={area_code})를 기준으로 TourAPI를 조회했습니다.",
            f"contentTypeId={EVENT_CONTENT_TYPE_ID}로 행사/공연/축제 후보를 선별했습니다.",
            f"호출 방식: {api_method_used}",
        ],
        "recommendations": _recommendations(destination),
        "debug_info": _build_debug_info(
            service_key,
            destination,
            area_code,
            api_method_used,
            "tour_api",
            None,
            None,
            area_status,
            area_count,
            supplemental_used,
            supplemental_count,
        ),
    }


def run(input_data):
    safe_input, destination, days, _user_request = _get_context(input_data)
    _area_name, area_code = _detect_area_code(safe_input)
    service_key = load_service_key()

    if requests is None:
        return _mock_event_result(destination, days, service_key, area_code, "missing_requests_dependency", "requests dependency is not available")
    if not _is_valid_service_key(service_key):
        return _mock_event_result(
            destination,
            days,
            service_key,
            area_code,
            "missing_or_placeholder_service_key",
            "TOUR_API_SERVICE_KEY is missing or still placeholder",
        )

    area_status = None
    area_count = 0
    last_error = None
    try:
        area_status, area_items = _fetch_area_based_raw_items(service_key, area_code)
        area_count = len(area_items)
        if area_items:
            return _tour_api_result(destination, days, service_key, area_code, "areaBasedList2", area_items, area_status, area_count)
        last_error = "areaBasedList2 returned no items"
    except Exception as exc:
        last_error = _safe_error(exc, "areaBasedList2")

    keyword_items = []
    for keyword in _candidate_keywords(destination):
        try:
            _status, items = _fetch_keyword_raw_items(service_key, keyword, area_code)
            keyword_items.extend(items)
        except Exception as exc:
            last_error = _safe_error(exc, "searchKeyword2")
            continue
    keyword_items = _unique_items(keyword_items)
    if keyword_items:
        return _tour_api_result(
            destination,
            days,
            service_key,
            area_code,
            "searchKeyword2",
            keyword_items,
            area_status,
            area_count,
            True,
            len(keyword_items),
        )

    return _mock_event_result(
        destination,
        days,
        service_key,
        area_code,
        "supplemental_empty",
        last_error or "supplemental_empty",
    )


if __name__ == "__main__":
    sample_input = {
        "destination": "제주",
        "location": "제주",
        "days": 3,
        "user_request": "제주 축제 행사 추천",
    }
    print(json.dumps(run(sample_input), ensure_ascii=False, indent=2))
