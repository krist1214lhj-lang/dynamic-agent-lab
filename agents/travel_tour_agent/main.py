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
TOUR_ATTRACTION_CONTENT_TYPE_ID = "12"
MAX_TOUR_ITEMS = 6
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
    "제주": "39"
}
SHOPPING_EXCLUDE_WORDS = [
    "아울렛",
    "백화점",
    "플래그십",
    "쇼핑",
    "면세점",
    "몰",
    "마트",
    "대여",
    "한복남"
]
TOUR_PRIORITY_WORDS = [
    "궁",
    "성",
    "공원",
    "해변",
    "전망대",
    "거리",
    "마을",
    "문화재",
    "사찰",
    "박물관",
    "전통",
    "자연",
    "랜드마크"
]
TOUR_CONTENT_TYPE_IDS = {"12", "14", "28"}
SHOPPING_CONTENT_TYPE_IDS = {"38"}
SEOUL_REPRESENTATIVE_KEYWORDS = [
    "경복궁",
    "창덕궁",
    "북촌",
    "남산",
    "청계천",
    "한강",
    "인사동",
    "덕수궁"
]
SEOUL_SUPPLEMENTAL_KEYWORDS = [
    "서울 경복궁",
    "서울 창덕궁",
    "서울 북촌한옥마을",
    "서울 남산서울타워",
    "서울 청계천",
    "서울 인사동",
    "서울 덕수궁",
    "서울 한강공원"
]
BUSAN_SUPPLEMENTAL_KEYWORDS = [
    "부산 해운대",
    "부산 광안리",
    "부산 감천문화마을",
    "부산 태종대",
    "부산 자갈치시장",
    "부산 송도해상케이블카",
    "부산 국제시장",
    "부산 오륙도"
]
SEOUL_HANGANG_PRIORITY_TITLES = [
    "여의도한강공원",
    "반포한강공원",
    "뚝섬한강공원",
    "잠실한강공원",
    "양화한강공원",
    "강서한강공원"
]
DETAIL_FACILITY_WORDS = [
    "박물관",
    "미술관",
    "체육관",
    "자전거도로",
    "다래나무",
    "향나무",
    "소극장",
    "인정문",
    "주차장",
    "안내소",
    "기념관",
    "호텔",
    "앰배서더",
    "게스트하우스"
]
CATEGORY_LABELS = {
    "12": "관광지",
    "14": "문화시설",
    "28": "레포츠",
    "A02020700": "공원/자연",
    "A02030100": "마을/거리",
    "A02010800": "역사/문화",
    "A02010100": "역사/문화",
    "A02010200": "역사/문화",
    "A02010300": "역사/문화",
    "A02010400": "역사/문화",
    "A02010500": "역사/문화",
    "A02010600": "역사/문화",
    "A02010700": "역사/문화",
    "A02030600": "전망/랜드마크",
    "A01010000": "자연",
    "A01020000": "자연",
}


class TourApiFallbackError(RuntimeError):
    def __init__(self, message, debug_info=None):
        super().__init__(message)
        self.debug_info = debug_info or {}


def _get_trip_context(input_data):
    safe_input = input_data if isinstance(input_data, dict) else {}
    location = (
        safe_input.get("destination")
        or safe_input.get("location")
        or "서울"
    )
    try:
        days = int(safe_input.get("days", safe_input.get("duration_days", 3)))
    except (TypeError, ValueError):
        days = 3
    period = safe_input.get("period", f"{days}일 여행")
    category = safe_input.get("category", "tour")
    keyword = safe_input.get("keyword", location)
    return safe_input, location, period, category, keyword


def load_service_key():
    """Load TourAPI service key from .env without exposing it."""
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

    return (
        os.getenv("TOURAPI_SERVICE_KEY")
        or os.getenv("TOUR_API_SERVICE_KEY")
        or os.getenv("KTO_SERVICE_KEY")
        or os.getenv("TOUR_SERVICE_KEY")
        or env_values.get("TOURAPI_SERVICE_KEY")
        or env_values.get("TOUR_API_SERVICE_KEY")
        or env_values.get("KTO_SERVICE_KEY")
        or env_values.get("TOUR_SERVICE_KEY")
    )


def _base_tour_api_params(service_key):
    return {
        "serviceKey": service_key,
        "MobileOS": TOUR_API_MOBILE_OS,
        "MobileApp": TOUR_API_MOBILE_APP,
        "_type": "json",
        "numOfRows": 12,
        "pageNo": 1
    }


def _normalize_items(items):
    if isinstance(items, list):
        return [item for item in items if isinstance(item, dict)]
    if isinstance(items, dict):
        return [items]
    return []


def _category_label(item):
    for key in ("cat3", "cat2", "cat1", "contenttypeid"):
        value = item.get(key)
        if value not in (None, ""):
            return CATEGORY_LABELS.get(str(value), "관광지")
    return "관광"


def _detect_area_code(input_data):
    safe_input, location, _period, _category, keyword = _get_trip_context(input_data)
    for value in (safe_input.get("destination"), safe_input.get("location"), location):
        if value in AREA_CODE_BY_NAME:
            return value, AREA_CODE_BY_NAME[value]

    search_text = " ".join(
        str(value)
        for value in [
            safe_input.get("user_request"),
            location,
            safe_input.get("destination"),
            keyword
        ]
        if value
    )

    for area_name, area_code in AREA_CODE_BY_NAME.items():
        if area_name in search_text:
            return area_name, area_code

    return None, None


def _to_tour_item(item):
    addr_parts = [
        str(item.get("addr1", "")).strip(),
        str(item.get("addr2", "")).strip()
    ]
    addr = " ".join(part for part in addr_parts if part)

    return {
        "title": str(item.get("title") or "제목 없음"),
        "addr": addr or "주소 정보 없음",
        "category": _category_label(item),
        "image": str(item.get("firstimage") or item.get("firstimage2") or ""),
        "mapx": str(item.get("mapx") or ""),
        "mapy": str(item.get("mapy") or ""),
        "contentid": str(item.get("contentid") or ""),
        "contenttypeid": str(item.get("contenttypeid") or "")
    }


def _contains_any(text, words):
    return any(word in text for word in words)


def _item_search_text(item):
    values = [
        item.get("title"),
        item.get("cat1"),
        item.get("cat2"),
        item.get("cat3"),
        item.get("contenttypeid"),
    ]
    return " ".join(str(value) for value in values if value not in (None, ""))


def _item_title(item):
    return str(item.get("title") or "")


def _item_identity(item):
    content_id = str(item.get("contentid") or "")
    if content_id:
        return f"contentid:{content_id}"
    return f"title:{_item_title(item)}"


def _is_representative_title(item):
    title = _item_title(item).replace(" ", "")
    representative_patterns = [
        "경복궁",
        "창덕궁",
        "북촌한옥마을",
        "남산서울타워",
        "청계천",
        "한강공원",
        "인사동",
        "덕수궁"
    ]
    return any(
        title == pattern or title.startswith(pattern)
        for pattern in representative_patterns
    )


def _representative_match_strength(item):
    title = _item_title(item).replace(" ", "")
    for keyword in SEOUL_REPRESENTATIVE_KEYWORDS:
        normalized_keyword = keyword.replace(" ", "")
        if title == normalized_keyword:
            return 3
        if title.startswith(normalized_keyword):
            return 2
        if normalized_keyword in title:
            return 1
    return 0


def _representative_keyword(item):
    title = _item_title(item).replace(" ", "")
    for keyword in SEOUL_REPRESENTATIVE_KEYWORDS:
        if keyword in title:
            return keyword
    return None


def _is_hangang_park(item):
    title = _item_title(item).replace(" ", "")
    return "한강" in title and "공원" in title


def _hangang_priority_rank(item):
    title = _item_title(item).replace(" ", "")
    for index, priority_title in enumerate(SEOUL_HANGANG_PRIORITY_TITLES):
        if priority_title in title:
            return index
    return None


def _is_gangseo_hangang(item):
    return _hangang_priority_rank(item) == SEOUL_HANGANG_PRIORITY_TITLES.index("강서한강공원")


def _apply_seoul_hangang_priority(items, area_name):
    if area_name != "서울":
        return items, False

    has_preferred_hangang = any(
        _is_hangang_park(item)
        and _hangang_priority_rank(item) is not None
        and not _is_gangseo_hangang(item)
        for item in items
    )
    if not has_preferred_hangang:
        return items, True

    return [
        item for item in items
        if not (_is_hangang_park(item) and _is_gangseo_hangang(item))
    ], True


def _allows_detail_facilities(input_data):
    safe_input, _location, _period, _category, _keyword = _get_trip_context(input_data)
    request_text = " ".join(
        str(value)
        for value in [
            safe_input.get("user_request"),
            safe_input.get("category"),
            safe_input.get("keyword")
        ]
        if value
    )
    return _contains_any(request_text, ["박물관", "미술관"])


def _is_detail_facility(item, input_data=None):
    if input_data is not None and _allows_detail_facilities(input_data):
        return False
    return _contains_any(_item_title(item), DETAIL_FACILITY_WORDS)


def _item_addr_text(item):
    return " ".join(
        str(item.get(key) or "")
        for key in ("addr1", "addr2")
    )


def _filter_items_by_area(items, area_name):
    if not area_name:
        return items
    return [
        item for item in items
        if isinstance(item, dict) and area_name in _item_addr_text(item)
    ]


def _tour_kind(item):
    text = _item_search_text(item)
    title = _item_title(item)
    category = _category_label(item)

    if _contains_any(title, ["경복궁", "창덕궁", "창경궁", "덕수궁", "경희궁"]):
        return "궁궐"
    if _contains_any(title, ["북촌", "한옥마을", "전통마을", "민속마을"]) or "마을/거리" in category:
        return "전통마을/거리"
    if _contains_any(title, ["남산", "타워", "전망대", "랜드마크"]):
        return "전망/랜드마크"
    if _contains_any(title, ["청계천", "거리", "길", "로데오", "골목"]):
        return "거리/산책"
    if _contains_any(title, ["한강", "강변", "하천"]):
        return "자연/한강"
    if _contains_any(text, ["공원", "근린공원", "생태공원"]) or "공원/자연" in category:
        return "공원"
    if _contains_any(text, ["산", "숲", "수목원", "자연", "해변"]):
        return "자연"
    if _contains_any(text, ["사찰", "절", "문화재", "유적", "성곽"]) or "역사/문화" in category:
        return "역사/문화"
    return category or "기타"


def _is_park_like(item):
    return _tour_kind(item) in {"공원", "자연/한강"}


def _is_shopping_like(item):
    content_type_id = str(item.get("contenttypeid") or "")
    if content_type_id in SHOPPING_CONTENT_TYPE_IDS:
        return True

    return _contains_any(_item_search_text(item), SHOPPING_EXCLUDE_WORDS)


def _tour_score(item, is_tour_request, input_data=None):
    content_type_id = str(item.get("contenttypeid") or "")
    search_text = _item_search_text(item)
    score = 0

    if content_type_id in TOUR_CONTENT_TYPE_IDS:
        score += 8
    if is_tour_request and _contains_any(search_text, TOUR_PRIORITY_WORDS):
        score += 5
    if str(item.get("firstimage") or item.get("firstimage2") or ""):
        score += 5
    if item.get("mapx") and item.get("mapy"):
        score += 1

    match_strength = _representative_match_strength(item)
    if match_strength == 3:
        score += 28
    elif match_strength == 2:
        score += 22
    elif match_strength == 1:
        score += 6

    if _is_detail_facility(item, input_data):
        score -= 30

    kind = _tour_kind(item)
    if kind in {"궁궐", "전통마을/거리", "전망/랜드마크", "거리/산책", "자연/한강"}:
        score += 4
    elif kind == "공원":
        score += 1

    area_name, _area_code = _detect_area_code(input_data or {})
    if area_name == "서울" and _is_hangang_park(item):
        hangang_rank = _hangang_priority_rank(item)
        if hangang_rank is not None:
            score += (len(SEOUL_HANGANG_PRIORITY_TITLES) - hangang_rank) * 10
        else:
            score += 5

    return score


def _is_tour_request(input_data):
    safe_input, _location, _period, category, _keyword = _get_trip_context(input_data)
    request_text = " ".join(
        str(value)
        for value in [
            safe_input.get("user_request"),
            safe_input.get("category"),
            category
        ]
        if value
    )
    return _contains_any(request_text, ["관광지", "명소", "볼거리", "투어", "여행지"])


def _select_diverse_items(prioritized_items, max_items=MAX_TOUR_ITEMS):
    selected = []
    selected_ids = set()
    kind_counts = {}
    representative_counts = {}
    park_like_count = 0

    for item in prioritized_items:
        identity = _item_identity(item)
        if identity in selected_ids:
            continue
        kind = _tour_kind(item)
        if kind_counts.get(kind, 0) >= 2:
            continue
        if _is_park_like(item) and park_like_count >= 2:
            continue
        representative_keyword = _representative_keyword(item)
        if representative_keyword and representative_counts.get(representative_keyword, 0) >= 1:
            continue
        selected.append(item)
        selected_ids.add(identity)
        kind_counts[kind] = kind_counts.get(kind, 0) + 1
        if _is_park_like(item):
            park_like_count += 1
        if representative_keyword:
            representative_counts[representative_keyword] = (
                representative_counts.get(representative_keyword, 0) + 1
            )
        if len(selected) >= max_items:
            break

    if len(selected) < max_items:
        for item in prioritized_items:
            identity = _item_identity(item)
            if identity in selected_ids:
                continue
            kind = _tour_kind(item)
            if kind_counts.get(kind, 0) >= 2:
                continue
            if _is_park_like(item) and park_like_count >= 2:
                continue
            representative_keyword = _representative_keyword(item)
            if representative_keyword and representative_counts.get(representative_keyword, 0) >= 1:
                continue
            selected.append(item)
            selected_ids.add(identity)
            kind_counts[kind] = kind_counts.get(kind, 0) + 1
            if _is_park_like(item):
                park_like_count += 1
            if representative_keyword:
                representative_counts[representative_keyword] = (
                    representative_counts.get(representative_keyword, 0) + 1
                )
            if len(selected) >= max_items:
                break

    return selected[:max_items]


def _filter_tour_api_items(raw_items, input_data, api_debug_info):
    is_tour_request = _is_tour_request(input_data)
    area_name = api_debug_info.get("area_name")
    non_shopping_items = [
        item for item in raw_items
        if not _is_shopping_like(item)
    ]
    excluded_count = len(raw_items) - len(non_shopping_items)

    if is_tour_request:
        prioritized = [
            item for item in non_shopping_items
            if _tour_score(item, is_tour_request, input_data) > 0
        ]
    else:
        prioritized = non_shopping_items[:]

    prioritized.sort(
        key=lambda item: _tour_score(item, is_tour_request, input_data),
        reverse=True
    )
    prioritized, hangang_priority_applied = _apply_seoul_hangang_priority(
        prioritized,
        area_name
    )

    selected = _select_diverse_items(prioritized)

    debug_info = {
        "raw_count": len(raw_items),
        "filtered_count": len(selected),
        "excluded_count": excluded_count,
        "diversity_filter_applied": True,
        "representative_filter_applied": True,
        "boosted_keywords": [
            keyword for keyword in SEOUL_REPRESENTATIVE_KEYWORDS
            if any(keyword in _item_title(item) for item in selected)
        ],
        "demoted_count": sum(
            1 for item in non_shopping_items
            if _is_detail_facility(item, input_data)
        ),
        "park_like_count": sum(1 for item in selected if _is_park_like(item)),
        "hangang_priority_applied": hangang_priority_applied,
        "final_count": len(selected[:MAX_TOUR_ITEMS]),
        **api_debug_info
    }
    return selected[:MAX_TOUR_ITEMS], debug_info


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

    raw_items = items.get("item", [])
    return _normalize_items(raw_items)


def _merge_unique_items(*item_groups):
    merged = []
    seen = set()
    for items in item_groups:
        for item in items:
            identity = _item_identity(item)
            if identity in seen:
                continue
            merged.append(item)
            seen.add(identity)
    return merged


def _fetch_keyword_raw_items(service_key, keyword, num_rows=12):
    params = _base_tour_api_params(service_key)
    params["keyword"] = keyword
    params["numOfRows"] = num_rows
    response = requests.get(
        f"{TOUR_API_BASE_URL}/searchKeyword2",
        params=params,
        timeout=5
    )
    response.raise_for_status()
    return _extract_raw_items(response.json())


def _fetch_area_based_raw_items(service_key, area_code):
    params = _base_tour_api_params(service_key)
    params["areaCode"] = area_code
    params["contentTypeId"] = TOUR_ATTRACTION_CONTENT_TYPE_ID
    params["arrange"] = "P"
    response = requests.get(
        f"{TOUR_API_BASE_URL}/areaBasedList2",
        params=params,
        timeout=5
    )
    response.raise_for_status()
    return _extract_raw_items(response.json())


def _item_image_url(item):
    return str(
        item.get("firstimage")
        or item.get("firstimage2")
        or item.get("originimgurl")
        or item.get("smallimageurl")
        or item.get("imgurl")
        or ""
    )


def _fetch_detail_image_url(service_key, content_id):
    if not content_id:
        return ""

    params = _base_tour_api_params(service_key)
    params["contentId"] = content_id
    params["imageYN"] = "Y"
    params["subImageYN"] = "Y"
    params["numOfRows"] = 10
    response = requests.get(
        f"{TOUR_API_BASE_URL}/detailImage2",
        params=params,
        timeout=5
    )
    response.raise_for_status()
    for image_item in _extract_raw_items(response.json()):
        image_url = _item_image_url(image_item)
        if image_url:
            return image_url
    return ""


def _image_enrichment_keyword(item):
    title = _item_title(item).strip()
    representative_keyword = _representative_keyword(item)
    return title or representative_keyword or ""


def _find_keyword_image_url(service_key, item, area_name):
    keyword = _image_enrichment_keyword(item)
    if not keyword:
        return ""

    content_id = str(item.get("contentid") or "")
    title = _item_title(item).replace(" ", "")
    representative_keyword = _representative_keyword(item)

    candidates = _fetch_keyword_raw_items(service_key, keyword, num_rows=10)
    candidates = _filter_items_by_area(candidates, area_name)
    candidates_with_images = [
        candidate for candidate in candidates
        if _item_image_url(candidate)
    ]
    if not candidates_with_images:
        return ""

    for candidate in candidates_with_images:
        if content_id and str(candidate.get("contentid") or "") == content_id:
            return _item_image_url(candidate)

    for candidate in candidates_with_images:
        if _item_title(candidate).replace(" ", "") == title:
            return _item_image_url(candidate)

    if representative_keyword:
        for candidate in candidates_with_images:
            if representative_keyword in _item_title(candidate):
                return _item_image_url(candidate)

    return _item_image_url(candidates_with_images[0])


def _enrich_missing_images(tour_items, service_key, area_name):
    enriched_items = [dict(item) for item in tour_items]
    attempted = False
    success_count = 0

    for item in enriched_items:
        if item.get("image"):
            continue

        attempted = True
        image_url = ""
        try:
            image_url = _find_keyword_image_url(service_key, item, area_name)
        except Exception:
            image_url = ""

        if not image_url:
            try:
                image_url = _fetch_detail_image_url(
                    service_key,
                    str(item.get("contentid") or "")
                )
            except Exception:
                image_url = ""

        if image_url:
            item["image"] = image_url
            success_count += 1

    return enriched_items[:MAX_TOUR_ITEMS], {
        "image_enrichment_attempted": attempted,
        "image_enrichment_success_count": success_count
    }


def _fetch_seoul_representative_items(service_key, area_name):
    if area_name != "서울":
        return [], []

    representative_items = []
    successful_keywords = []
    for keyword in SEOUL_SUPPLEMENTAL_KEYWORDS:
        try:
            items = _fetch_keyword_raw_items(service_key, keyword, num_rows=3)
            if not items:
                items = _fetch_keyword_raw_items(
                    service_key,
                    keyword.replace("서울 ", ""),
                    num_rows=3
                )
            representative_items.extend(items)
            successful_keywords.append(keyword)
        except Exception:
            continue
    return [
        item for item in _filter_items_by_area(representative_items, area_name)
        if _representative_keyword(item)
    ], successful_keywords


def _fetch_area_supplemental_items(service_key, area_name):
    if area_name == "서울":
        return _fetch_seoul_representative_items(service_key, area_name)
    if area_name != "부산":
        return [], []

    supplemental_items = []
    successful_keywords = []
    for keyword in BUSAN_SUPPLEMENTAL_KEYWORDS:
        try:
            items = _fetch_keyword_raw_items(service_key, keyword, num_rows=5)
            filtered_items = _filter_items_by_area(items, area_name)
            if filtered_items:
                supplemental_items.extend(filtered_items)
                successful_keywords.append(keyword)
        except Exception:
            continue
    return supplemental_items, successful_keywords


def _parse_tour_api_payload(raw_items, input_data, api_debug_info):
    filtered_items, debug_info = _filter_tour_api_items(
        raw_items,
        input_data,
        api_debug_info
    )
    return [_to_tour_item(item) for item in filtered_items], debug_info


def fetch_tour_api_items(input_data, service_key):
    """Call TourAPI best-effort. Raises on failure so run() can fallback safely."""
    if requests is None:
        raise RuntimeError("missing_dependency: requests")
    if not service_key:
        raise RuntimeError("missing_service_key")

    _safe_input, _location, _period, _category, keyword = _get_trip_context(input_data)
    area_name, area_code = _detect_area_code(input_data)
    keyword = str(keyword or "").strip()
    endpoint = "areaBasedList2" if area_code else "searchKeyword2"
    primary_raw_items = []
    area_based_raw_count = 0
    area_based_error = None
    fallback_reason = None
    debug_message = "tour_api_success"
    supplemental_attempted = False

    def fallback_debug(debug_message_value, supplemental_items=None, supplemental_keywords=None):
        supplemental_items = supplemental_items or []
        supplemental_keywords = supplemental_keywords or []
        return {
            "destination": area_name or _location,
            "endpoint_used": endpoint,
            "api_method_used": (
                "area_code_content_type_plus_supplemental_keyword"
                if supplemental_keywords
                else (
                    "area_code_content_type"
                    if endpoint == "areaBasedList2"
                    else "keyword_search"
                )
            ),
            "area_code": area_code,
            "area_name": area_name,
            "area_based_raw_count": area_based_raw_count,
            "content_type_id": (
                TOUR_ATTRACTION_CONTENT_TYPE_ID
                if endpoint == "areaBasedList2"
                else None
            ),
            "supplemental_search_used": supplemental_attempted,
            "supplemental_success_count": len(supplemental_items),
            "supplemental_keywords": supplemental_keywords,
            "fallback_reason": debug_message_value,
            "debug_message": debug_message_value,
            "final_count": 0
        }

    if endpoint == "areaBasedList2":
        try:
            primary_raw_items = _fetch_area_based_raw_items(service_key, area_code)
            area_based_raw_count = len(primary_raw_items)
        except Exception as exc:
            area_based_error = type(exc).__name__
            fallback_reason = "tour_api_http_error"
    else:
        try:
            primary_raw_items = _fetch_keyword_raw_items(service_key, keyword)
        except Exception as exc:
            fallback_reason = "tour_api_http_error"
            raise TourApiFallbackError(
                fallback_reason,
                fallback_debug(fallback_reason)
            ) from exc

    primary_area_items = _filter_items_by_area(primary_raw_items, area_name)
    should_use_supplemental = (
        area_name == "서울"
        or (area_name == "부산" and (area_based_error is not None or not primary_area_items))
    )
    representative_raw_items = []
    supplemental_keywords = []
    if should_use_supplemental:
        supplemental_attempted = True
        representative_raw_items, supplemental_keywords = _fetch_area_supplemental_items(
            service_key,
            area_name
        )

    supplemental_success_count = len(representative_raw_items)
    if area_name == "부산" and not primary_area_items:
        if supplemental_success_count > 0:
            debug_message = "area_based_empty_then_supplemental_success"
            if area_based_error:
                fallback_reason = f"area_based_failed_then_supplemental_success:{area_based_error}"
        else:
            debug_message = (
                "tour_api_http_error"
                if area_based_error
                else "area_based_empty_and_supplemental_empty"
            )
            raise TourApiFallbackError(
                debug_message,
                fallback_debug(debug_message, representative_raw_items, supplemental_keywords)
            )

    raw_items = _merge_unique_items(
        representative_raw_items,
        primary_area_items
    )
    if not raw_items:
        debug_message = "area_based_empty_and_supplemental_empty"
        raise TourApiFallbackError(
            debug_message,
            fallback_debug(debug_message, representative_raw_items, supplemental_keywords)
        )

    api_debug_info = {
        "destination": area_name or _location,
        "endpoint_used": endpoint,
        "api_method_used": (
            "area_code_content_type_plus_supplemental_keyword"
            if supplemental_keywords
            else (
                "area_code_content_type"
                if endpoint == "areaBasedList2"
                else "keyword_search"
            )
        ),
        "area_code": area_code,
        "area_name": area_name,
        "area_based_raw_count": area_based_raw_count,
        "content_type_id": (
            TOUR_ATTRACTION_CONTENT_TYPE_ID
            if endpoint == "areaBasedList2"
            else None
        ),
        "representative_candidates": len(representative_raw_items),
        "supplemental_search_used": supplemental_attempted,
        "supplemental_success_count": supplemental_success_count,
        "supplemental_keywords": supplemental_keywords,
        "merged_count": len(representative_raw_items) + len(primary_raw_items),
        "deduped_count": len(raw_items),
        "fallback_reason": fallback_reason,
        "debug_message": debug_message
    }
    items, debug_info = _parse_tour_api_payload(raw_items, input_data, api_debug_info)
    if not items:
        raise TourApiFallbackError(
            "area_based_empty_and_supplemental_empty",
            fallback_debug(
                "area_based_empty_and_supplemental_empty",
                representative_raw_items,
                supplemental_keywords
            )
        )
    items, image_debug_info = _enrich_missing_images(items, service_key, area_name)
    debug_info.update(image_debug_info)
    debug_info["final_count"] = len(items[:MAX_TOUR_ITEMS])
    debug_info["fallback_reason"] = fallback_reason
    debug_info["debug_message"] = debug_message
    return endpoint, items, debug_info


def build_mock_tour_result(input_data, fallback_reason="mock_fallback", fallback_debug_info=None):
    _safe_input, location, period, category, _keyword = _get_trip_context(input_data)
    area_name, area_code = _detect_area_code(input_data)

    if location == "부산":
        tour_items = [
            {
                "title": "해운대해수욕장",
                "addr": "부산광역시 해운대구 해운대해변로",
                "category": "관광지",
                "image": "https://example.com/images/haeundae.jpg",
                "mapx": "129.160384",
                "mapy": "35.158698"
            },
            {
                "title": "감천문화마을",
                "addr": "부산광역시 사하구 감내2로 203",
                "category": "마을/거리",
                "image": "https://example.com/images/gamcheon-culture-village.jpg",
                "mapx": "129.010593",
                "mapy": "35.097489"
            },
            {
                "title": "광안리해수욕장",
                "addr": "부산광역시 수영구 광안해변로",
                "category": "관광지",
                "image": "https://example.com/images/gwangalli.jpg",
                "mapx": "129.118550",
                "mapy": "35.153170"
            }
        ]
    else:
        tour_items = [
            {
                "title": "경복궁",
                "addr": "서울특별시 종로구 사직로 161",
                "category": "관광지",
                "image": "https://example.com/images/gyeongbokgung.jpg",
                "mapx": "126.976888",
                "mapy": "37.579617"
            },
            {
                "title": "남산서울타워",
                "addr": "서울특별시 용산구 남산공원길 105",
                "category": "전망/랜드마크",
                "image": "https://example.com/images/namsan-tower.jpg",
                "mapx": "126.988228",
                "mapy": "37.551169"
            },
            {
                "title": "북촌한옥마을",
                "addr": "서울특별시 종로구 계동길 37",
                "category": "문화/거리",
                "image": "https://example.com/images/bukchon-hanok.jpg",
                "mapx": "126.986661",
                "mapy": "37.582604"
            }
        ]
    if area_code:
        lookup_message = (
            f"{area_name or location} 지역코드(areaCode={area_code})를 인식해 TourAPI를 조회했습니다."
        )
    else:
        lookup_message = "지역코드를 인식하지 못해 mock fallback 결과를 반환했습니다."

    if location == "부산":
        recommendations = [
            "해운대와 광안리는 해안 동선으로 묶고, 감천문화마을은 별도 반나절 일정으로 배치하면 좋습니다.",
            "해변 일정은 날씨와 바람 영향을 받으므로 실내 대체 관광지를 함께 준비하세요.",
            "향후 TourAPI 연결 후에는 부산 지역 코드, 콘텐츠 타입, 이미지 유무 기준으로 후보를 필터링하세요."
        ]
    else:
        recommendations = [
            "동선은 경복궁과 북촌한옥마을을 같은 날에 묶으면 이동 부담을 줄일 수 있습니다.",
            "남산서울타워는 날씨가 맑은 날 오후나 야간 일정으로 배치하는 것이 좋습니다.",
            "향후 TourAPI 연결 후에는 지역 코드, 콘텐츠 타입, 이미지 유무 기준으로 후보를 필터링하세요."
        ]

    debug_info = {
        "destination": area_name or location,
        "area_code": area_code,
        "area_name": area_name,
        "api_method_used": (
            "mock_fallback_after_area_code_detection"
            if area_code
            else "mock_fallback_without_area_code"
        ),
        "area_based_raw_count": 0,
        "supplemental_search_used": False,
        "supplemental_success_count": 0,
        "final_count": len(tour_items),
        "fallback_reason": fallback_reason
    }
    if fallback_debug_info:
        debug_info.update(fallback_debug_info)
        debug_info["final_count"] = len(tour_items)
        debug_info["fallback_reason"] = fallback_reason

    return {
        "agent": "travel_tour_agent",
        "data_source": "mock_fallback",
        "summary": (
            f"Mock tour candidates for {location} during a {period}. "
            f"Requested category hint: {category}."
        ),
        "tour_items": tour_items,
        "tour_findings": [
            "관광지, 랜드마크, 문화 거리 유형을 섞어 mock 후보를 구성했습니다.",
            lookup_message,
            "좌표와 이미지 필드는 향후 TourAPI 응답을 담을 수 있는 형태로 유지했습니다.",
            "현재 데이터는 실제 운영 시간, 휴무일, 행사 일정과 다를 수 있습니다."
        ],
        "recommendations": recommendations,
        "risks": [
            "현재 결과는 mock 데이터이므로 실제 행사, 숙박, 운영 정보와 일치하지 않을 수 있습니다.",
            "이미지 URL은 예시 값이며 실제 이미지 파일을 보장하지 않습니다.",
            "혼잡도와 예약 가능 여부는 별도 확인이 필요합니다."
        ],
        "next_agents": [
            "travel_schedule_agent",
            "travel_weather_agent",
            "travel_budget_agent"
        ],
        "debug_info": debug_info,
        "debug_message": fallback_reason
    }


def build_tour_api_result(input_data, endpoint, tour_items, debug_info):
    safe_input, location, _period, category, keyword = _get_trip_context(input_data)
    try:
        days = int(safe_input.get("days", safe_input.get("duration_days", 3)))
    except (TypeError, ValueError):
        days = 3

    if debug_info.get("area_code"):
        lookup_message = (
            f"{debug_info.get('area_name') or location} 지역코드"
            f"(areaCode={debug_info['area_code']})를 인식해 TourAPI를 조회했습니다."
        )
    else:
        lookup_message = (
            f"지역코드를 인식하지 못해 searchKeyword2로 keyword={keyword} 검색을 수행했습니다."
        )
    tour_findings = [
        "한국관광공사 TourAPI 응답을 기존 tour_items 구조로 변환했습니다.",
        lookup_message,
        "TourAPI 결과에서 쇼핑/상업시설을 제외하고 관광지 성격의 항목을 우선 선별했습니다.",
        "공원류 중복을 줄이고 대표 관광지 유형이 섞이도록 선별했습니다.",
        "대표 관광지를 우선하고, 세부 시설/부속 항목은 낮은 우선순위로 조정했습니다.",
        "이미지가 없는 대표 관광지는 TourAPI 보조 검색으로 이미지 보강을 시도했습니다.",
        f"호출 엔드포인트는 {endpoint}입니다.",
        "이미지, 주소, 좌표는 API 응답에 존재하는 값만 반영했습니다."
    ]
    if debug_info.get("area_name") == "서울":
        tour_findings.insert(
            5,
            "대표 관광지 키워드별 TourAPI 보조 검색을 사용해 후보를 보강했습니다."
        )
        if debug_info.get("hangang_priority_applied"):
            tour_findings.insert(
                7,
                "서울 한강공원 후보는 대표성이 높은 후보를 우선하도록 조정했습니다."
            )

    return {
        "agent": "travel_tour_agent",
        "data_source": "tour_api",
        "summary": (
            f"TourAPI {endpoint} results for {location} during a {days}일 여행."
        ),
        "tour_items": tour_items,
        "tour_findings": tour_findings,
        "recommendations": [
            "지도 표시에는 mapx, mapy 값을 사용하세요.",
            "이미지가 없는 항목은 웹 화면의 기본 이미지 없음 박스로 표시됩니다.",
            "상세 정보가 필요하면 contentid 기반 상세 조회 API를 후속 연결하세요."
        ],
        "risks": [
            "TourAPI 응답 항목은 운영 시간, 예약 가능 여부, 요금 정보를 항상 포함하지 않을 수 있습니다.",
            "검색 키워드에 따라 지역 외 후보가 일부 섞일 수 있습니다.",
            "API 장애나 응답 형식 변경 시 mock_fallback으로 전환됩니다."
        ],
        "next_agents": [
            "travel_schedule_agent",
            "travel_weather_agent",
            "travel_budget_agent"
        ],
        "debug_info": debug_info,
        "debug_message": debug_info.get("debug_message", "tour_api_success")
    }


def run(input_data):
    """Return TourAPI candidates when available, otherwise return mock fallback."""
    safe_input = input_data if isinstance(input_data, dict) else {}
    fallback_reason = "missing_service_key"
    fallback_debug_info = None
    try:
        service_key = load_service_key()
        if service_key:
            endpoint, tour_items, debug_info = fetch_tour_api_items(safe_input, service_key)
            return build_tour_api_result(safe_input, endpoint, tour_items, debug_info)
    except TourApiFallbackError as exc:
        fallback_reason = str(exc) or "tour_api_http_error"
        fallback_debug_info = exc.debug_info
    except Exception as exc:
        fallback_reason = type(exc).__name__

    return build_mock_tour_result(safe_input, fallback_reason, fallback_debug_info)


if __name__ == "__main__":
    sample_input = {
        "user_request": "부산 2박 3일 여행지 추천하고 관광지도 알려줘.",
        "destination": "부산",
        "location": "부산",
        "origin": "서울",
        "days": 3,
        "category": "관광지"
    }
    print(json.dumps(run(sample_input), ensure_ascii=False, indent=2))
