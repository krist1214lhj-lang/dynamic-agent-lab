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


TOUR_API_BASE_URL = "https://apis.data.go.kr/B551011/KorService2"
TOUR_API_MOBILE_OS = "ETC"
TOUR_API_MOBILE_APP = "dynamic-agent-lab"
TOUR_FOOD_CONTENT_TYPE_ID = "39"
MAX_FOOD_ITEMS = 6

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

FOOD_SEARCH_KEYWORDS = [
    "{destination} 맛집",
    "{destination} 음식점",
    "{destination} 향토음식",
    "{destination} 로컬푸드",
]

MOCK_FOOD_ITEMS = {
    "제주": [
        {
            "name": "흑돼지거리",
            "address": "제주특별자치도 제주시 연동 일대",
            "category": "제주 음식",
            "menu_hint": "흑돼지",
            "meal_time": "저녁",
            "image": "https://example.com/images/jeju-black-pork.jpg",
            "mapx": "126.495",
            "mapy": "33.489",
        },
        {
            "name": "고기국수 거리",
            "address": "제주특별자치도 제주시 일대",
            "category": "국수",
            "menu_hint": "고기국수",
            "meal_time": "점심",
            "image": "https://example.com/images/jeju-gogi-guksu.jpg",
            "mapx": "126.53",
            "mapy": "33.51",
        },
        {
            "name": "갈치조림 전문식당",
            "address": "제주특별자치도 서귀포시",
            "category": "해산물",
            "menu_hint": "갈치조림",
            "meal_time": "점심/저녁",
            "image": "https://example.com/images/jeju-cutlassfish.jpg",
            "mapx": "126.56",
            "mapy": "33.25",
        },
        {
            "name": "해산물 식당",
            "address": "제주특별자치도 서귀포시 해안가",
            "category": "해산물",
            "menu_hint": "해산물 모듬",
            "meal_time": "저녁",
            "image": "https://example.com/images/jeju-seafood.jpg",
            "mapx": "126.57",
            "mapy": "33.24",
        },
    ],
    "부산": [
        {
            "name": "돼지국밥집",
            "address": "부산광역시 중구 일대",
            "category": "국밥",
            "menu_hint": "돼지국밥",
            "meal_time": "아침/점심",
            "image": "https://example.com/images/busan-pork-rice-soup.jpg",
            "mapx": "129.031",
            "mapy": "35.101",
        },
        {
            "name": "밀면 전문점",
            "address": "부산광역시 해운대구 일대",
            "category": "면요리",
            "menu_hint": "밀면",
            "meal_time": "점심",
            "image": "https://example.com/images/busan-milmyeon.jpg",
            "mapx": "129.164",
            "mapy": "35.159",
        },
        {
            "name": "자갈치 회센터",
            "address": "부산광역시 중구 자갈치로",
            "category": "해산물",
            "menu_hint": "회 / 해산물",
            "meal_time": "저녁",
            "image": "https://example.com/images/busan-jagalchi.jpg",
            "mapx": "129.030",
            "mapy": "35.097",
        },
        {
            "name": "씨앗호떡 거리",
            "address": "부산광역시 중구 남포동",
            "category": "간식",
            "menu_hint": "씨앗호떡",
            "meal_time": "간식",
            "image": "https://example.com/images/busan-ssiathotteok.jpg",
            "mapx": "129.032",
            "mapy": "35.100",
        },
    ],
    "전주": [
        {
            "name": "전주비빔밥 식당",
            "address": "전북특별자치도 전주시 완산구",
            "category": "한식",
            "menu_hint": "비빔밥",
            "meal_time": "점심",
            "image": "https://example.com/images/jeonju-bibimbap.jpg",
            "mapx": "127.147",
            "mapy": "35.819",
        },
        {
            "name": "한정식 맛집",
            "address": "전북특별자치도 전주시 완산구",
            "category": "한식",
            "menu_hint": "한정식",
            "meal_time": "점심/저녁",
            "image": "https://example.com/images/jeonju-hanjeongsik.jpg",
            "mapx": "127.14",
            "mapy": "35.82",
        },
        {
            "name": "콩나물국밥집",
            "address": "전북특별자치도 전주시 덕진구",
            "category": "국밥",
            "menu_hint": "콩나물국밥",
            "meal_time": "아침",
            "image": "https://example.com/images/jeonju-kongnamul-gukbap.jpg",
            "mapx": "127.13",
            "mapy": "35.83",
        },
    ],
    "강릉": [
        {
            "name": "초당두부 마을",
            "address": "강원특별자치도 강릉시 초당동",
            "category": "두부요리",
            "menu_hint": "초당두부",
            "meal_time": "아침/점심",
            "image": "https://example.com/images/gangneung-chodang-tofu.jpg",
            "mapx": "128.915",
            "mapy": "37.791",
        },
        {
            "name": "장칼국수 맛집",
            "address": "강원특별자치도 강릉시 교동",
            "category": "면요리",
            "menu_hint": "장칼국수",
            "meal_time": "점심",
            "image": "https://example.com/images/gangneung-jang-kalguksu.jpg",
            "mapx": "128.895",
            "mapy": "37.751",
        },
        {
            "name": "커피거리 카페",
            "address": "강원특별자치도 강릉시 안목해변",
            "category": "카페",
            "menu_hint": "커피 / 디저트",
            "meal_time": "간식",
            "image": "https://example.com/images/gangneung-coffee-street.jpg",
            "mapx": "128.948",
            "mapy": "37.769",
        },
    ],
    "여수": [
        {
            "name": "게장백반집",
            "address": "전라남도 여수시 일대",
            "category": "해산물",
            "menu_hint": "게장",
            "meal_time": "점심/저녁",
            "image": "https://example.com/images/yeosu-marinated-crab.jpg",
            "mapx": "127.662",
            "mapy": "34.760",
        },
        {
            "name": "해산물 식당",
            "address": "전라남도 여수시 종화동",
            "category": "해산물",
            "menu_hint": "해산물 모듬",
            "meal_time": "저녁",
            "image": "https://example.com/images/yeosu-seafood.jpg",
            "mapx": "127.738",
            "mapy": "34.747",
        },
        {
            "name": "갓김치 한상",
            "address": "전라남도 여수시 중앙동",
            "category": "지역음식",
            "menu_hint": "갓김치",
            "meal_time": "점심",
            "image": "https://example.com/images/yeosu-gatkimchi.jpg",
            "mapx": "127.732",
            "mapy": "34.741",
        },
    ],
    "서울": [
        {
            "name": "한식 한상",
            "address": "서울특별시 종로구",
            "category": "한식",
            "menu_hint": "한식 백반",
            "meal_time": "점심/저녁",
            "image": "https://example.com/images/seoul-korean.jpg",
            "mapx": "126.978",
            "mapy": "37.566",
        },
        {
            "name": "분식 거리",
            "address": "서울특별시 중구",
            "category": "분식",
            "menu_hint": "떡볶이, 김밥",
            "meal_time": "간식",
            "image": "https://example.com/images/seoul-snack-street.jpg",
            "mapx": "126.983",
            "mapy": "37.563",
        },
        {
            "name": "시장 음식점",
            "address": "서울특별시 중구",
            "category": "시장 음식",
            "menu_hint": "시장 국수 / 튀김",
            "meal_time": "점심",
            "image": "https://example.com/images/seoul-market-food.jpg",
            "mapx": "126.991",
            "mapy": "37.57",
        },
        {
            "name": "카페 거리",
            "address": "서울특별시 마포구",
            "category": "카페",
            "menu_hint": "커피 / 디저트",
            "meal_time": "간식",
            "image": "https://example.com/images/seoul-cafe.jpg",
            "mapx": "126.923",
            "mapy": "37.554",
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


def _load_env():
    env_path = Path(__file__).with_name(".env")
    if load_dotenv is not None:
        load_dotenv(dotenv_path=env_path)

    env_values = {}
    if env_path.exists():
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue
                key, value = stripped.split("=", 1)
                env_values[key.strip()] = value.strip().strip("\"'")
        except OSError:
            env_values = {}
    return env_values


def load_service_key():
    env_values = _load_env()
    return (
        os.getenv("TOUR_API_SERVICE_KEY")
        or env_values.get("TOUR_API_SERVICE_KEY")
        or os.getenv("TOURAPI_SERVICE_KEY")
        or env_values.get("TOURAPI_SERVICE_KEY")
        or os.getenv("KTO_SERVICE_KEY")
        or env_values.get("KTO_SERVICE_KEY")
    )


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


def _contains_any(text, words):
    return any(word in text for word in words)


def _get_context(input_data):
    safe_input = _safe_dict(input_data)
    destination = (
        safe_input.get("destination")
        or safe_input.get("location")
        or _detect_destination_from_text(safe_input.get("user_request", ""))
        or "서울"
    )
    if destination not in AREA_CODE_BY_NAME and destination in {"강릉", "속초", "춘천"}:
        destination = destination
    days = _safe_int(safe_input.get("days", safe_input.get("duration_days", 3)), 3)
    budget_level = str(safe_input.get("budget_level") or "medium")
    user_request = str(safe_input.get("user_request") or "")
    return safe_input, destination, days, budget_level, user_request


def _detect_destination_from_text(text):
    search_text = str(text or "")
    for region in REGION_PRIORITY:
        if region in search_text:
            return region
    return None


def _detect_area_code(input_data):
    safe_input, destination, _days, _budget_level, user_request = _get_context(input_data)
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
        for alias, area_code in (
            ("강릉", "32"),
            ("속초", "32"),
            ("춘천", "32"),
            ("전주", "37"),
            ("여수", "38"),
            ("경주", "35"),
        ):
            if alias in candidate:
                return alias, area_code
    for region in REGION_PRIORITY:
        if region in user_request:
            if region in AREA_CODE_BY_NAME:
                return region, AREA_CODE_BY_NAME[region]
            if region in {"강릉", "속초", "춘천"}:
                return region, "32"
            if region == "전주":
                return region, "37"
            if region == "여수":
                return region, "38"
            if region == "경주":
                return region, "35"
    return "서울", AREA_CODE_BY_NAME["서울"]


def _item_text(item):
    return " ".join(
        str(item.get(key) or "")
        for key in ("title", "cat1", "cat2", "cat3", "firstmenu", "treatmenu", "menu")
    )


def _item_address(item):
    address = " ".join(
        str(item.get(key) or "").strip()
        for key in ("addr1", "addr2")
    ).strip()
    return address or "주소 정보 없음"


def _item_image(item):
    return str(
        item.get("firstimage")
        or item.get("firstimage2")
        or item.get("originimgurl")
        or item.get("smallimageurl")
        or item.get("imgurl")
        or ""
    )


def _to_food_item(item):
    menu_hint = (
        item.get("firstmenu")
        or item.get("treatmenu")
        or item.get("menu")
        or item.get("signaturemenu")
        or "대표 메뉴 정보 없음"
    )
    meal_time = (
        item.get("opentimefood")
        or item.get("opentime")
        or item.get("openinghours")
        or "점심/저녁"
    )
    category = item.get("cat3") or item.get("cat2") or item.get("cat1") or "맛집"
    return {
        "name": str(item.get("title") or "제목 없음"),
        "address": _item_address(item),
        "category": str(category),
        "menu_hint": str(menu_hint),
        "meal_time": str(meal_time),
        "image": _item_image(item),
        "mapx": str(item.get("mapx") or ""),
        "mapy": str(item.get("mapy") or ""),
    }


def _base_food_items(destination):
    if destination in MOCK_FOOD_ITEMS:
        return [dict(item) for item in MOCK_FOOD_ITEMS[destination]]
    return [dict(item) for item in MOCK_FOOD_ITEMS["서울"]]


def _mock_recommendations(destination, budget_level):
    if destination == "제주":
        return [
            "흑돼지와 고기국수는 점심/저녁 동선으로 묶으면 이동이 편합니다.",
            "해산물 식당은 해안가 일정과 함께 잡으면 좋습니다.",
            f"예산이 {budget_level}이면 대표 메뉴를 하나씩 고르는 방식이 효율적입니다.",
        ]
    if destination == "부산":
        return [
            "돼지국밥과 밀면을 낮 동선에 넣고, 저녁은 자갈치 회를 고려하세요.",
            "씨앗호떡은 관광 동선 사이 간식으로 넣기 좋습니다.",
            f"예산이 {budget_level}이면 해산물과 로컬 국밥을 균형 있게 배치하세요.",
        ]
    if destination == "전주":
        return [
            "비빔밥과 한정식을 중심으로 한식 코스를 구성하세요.",
            "콩나물국밥은 아침 일정에 넣기 좋습니다.",
            f"예산이 {budget_level}이면 전주 한식 대표 메뉴를 우선 추천합니다.",
        ]
    if destination == "강릉":
        return [
            "초당두부와 장칼국수, 커피거리를 함께 묶으면 동선이 좋습니다.",
            "해변 산책과 식사를 연결하면 여행 만족도가 높습니다.",
            f"예산이 {budget_level}이면 점심은 식사, 오후는 카페 중심으로 구성하세요.",
        ]
    if destination == "여수":
        return [
            "게장과 해산물은 저녁 일정에 넣는 것이 좋습니다.",
            "갓김치는 기념품용으로도 고려할 수 있습니다.",
            f"예산이 {budget_level}이면 해산물 1회와 로컬 음식 1회를 섞어보세요.",
        ]
    return [
        "시장 음식과 한식, 카페를 섞으면 무난합니다.",
        "관광 동선과 가까운 식당을 먼저 잡으면 이동이 편합니다.",
        f"예산이 {budget_level}이면 한 끼는 로컬 음식, 한 끼는 가벼운 분식으로 구성하세요.",
    ]


def _mock_food_result(destination, days, budget_level, reason="mock_fallback"):
    food_items = _base_food_items(destination)
    return {
        "agent": "travel_food_agent",
        "summary": f"Mock food suggestions for {destination} during a {days}일 여행.",
        "destination": destination,
        "data_source": "mock_fallback",
        "food_items": food_items,
        "food_findings": [
            f"{destination} 기준 지역 음식 후보를 mock 데이터로 구성했습니다.",
            "실제 영업시간과 예약 가능 여부는 별도 확인이 필요합니다.",
            f"fallback_reason={reason}",
        ],
        "recommendations": _mock_recommendations(destination, budget_level),
        "debug_info": {
            "destination": destination,
            "area_code": AREA_CODE_BY_NAME.get(destination, AREA_CODE_BY_NAME["서울"]),
            "content_type_id": 39,
            "api_method_used": "mock_fallback",
            "data_source": "mock_fallback",
        },
    }


def _fetch_area_based_raw_items(service_key, area_code):
    params = _base_params(service_key)
    params["areaCode"] = area_code
    params["contentTypeId"] = TOUR_FOOD_CONTENT_TYPE_ID
    params["arrange"] = "P"
    response = requests.get(
        f"{TOUR_API_BASE_URL}/areaBasedList2",
        params=params,
        timeout=6,
    )
    response.raise_for_status()
    return _extract_raw_items(response.json())


def _fetch_keyword_raw_items(service_key, keyword, area_code):
    params = _base_params(service_key)
    params["keyword"] = keyword
    params["areaCode"] = area_code
    params["contentTypeId"] = TOUR_FOOD_CONTENT_TYPE_ID
    params["arrange"] = "P"
    response = requests.get(
        f"{TOUR_API_BASE_URL}/searchKeyword2",
        params=params,
        timeout=6,
    )
    response.raise_for_status()
    return _extract_raw_items(response.json())


def _candidate_keywords(destination):
    return [keyword.format(destination=destination) for keyword in FOOD_SEARCH_KEYWORDS]


def _unique_items(items):
    seen = set()
    unique = []
    for item in items:
        key = str(item.get("contentid") or item.get("title") or "")
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _pick_food_items(raw_items):
    filtered = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "")
        if not title:
            continue
        filtered.append(item)
    filtered = _unique_items(filtered)
    filtered.sort(
        key=lambda item: (
            1 if _item_image(item) else 0,
            1 if _item_address(item) != "주소 정보 없음" else 0,
            len(_item_text(item)),
        ),
        reverse=True,
    )
    return filtered[:MAX_FOOD_ITEMS]


def _build_tour_api_result(destination, days, budget_level, area_code, api_method_used, raw_items):
    food_items = [_to_food_item(item) for item in _pick_food_items(raw_items)]
    return {
        "agent": "travel_food_agent",
        "summary": f"TourAPI food results for {destination} during a {days}일 여행.",
        "destination": destination,
        "data_source": "tour_api",
        "food_items": food_items,
        "food_findings": [
            f"지역코드(areaCode={area_code})를 기준으로 TourAPI를 조회했습니다.",
            f"contentTypeId={TOUR_FOOD_CONTENT_TYPE_ID}로 음식점 후보를 우선 선별했습니다.",
            f"호출 방식: {api_method_used}",
            "검색 결과를 food_items 구조로 변환했습니다.",
        ],
        "recommendations": [
            "점심과 저녁을 나눠서 동선을 구성하면 이동 부담이 줄어듭니다.",
            "대표 메뉴와 영업시간은 실제 방문 전에 다시 확인하세요.",
            f"예산이 {budget_level}이면 로컬 대표 음식과 간단한 카페를 섞어보세요.",
        ],
        "debug_info": {
            "destination": destination,
            "area_code": area_code,
            "content_type_id": 39,
            "api_method_used": api_method_used,
            "data_source": "tour_api",
        },
    }


def run(input_data):
    safe_input, destination, days, budget_level, user_request = _get_context(input_data)
    area_name, area_code = _detect_area_code(safe_input)
    service_key = load_service_key()

    if requests is None or not service_key:
        return _mock_food_result(destination, days, budget_level, "missing_dependency_or_service_key")

    api_method_used = "areaBasedList2"
    try:
        area_items = _fetch_area_based_raw_items(service_key, area_code)
        if area_items:
            return _build_tour_api_result(
                destination,
                days,
                budget_level,
                area_code,
                api_method_used,
                area_items,
            )
    except Exception:
        area_items = []

    try:
        api_method_used = "searchKeyword2"
        keyword_items = []
        for keyword in _candidate_keywords(destination):
            try:
                keyword_items.extend(_fetch_keyword_raw_items(service_key, keyword, area_code))
            except Exception:
                continue
        keyword_items = _unique_items(keyword_items)
        if keyword_items:
            return _build_tour_api_result(
                destination,
                days,
                budget_level,
                area_code,
                api_method_used,
                keyword_items,
            )
    except Exception:
        pass

    return _mock_food_result(destination, days, budget_level, "tour_api_empty_or_failed")


if __name__ == "__main__":
    sample_input = {
        "destination": "제주",
        "location": "제주",
        "days": 3,
        "budget_level": "medium",
        "user_request": "제주 맛집 추천",
    }
    print(json.dumps(run(sample_input), ensure_ascii=False, indent=2))
