import math

BUDGET_UNIT_PRICES = {
    "low":    {"meal_per_count": 10000, "lodging_per_night": 60000,  "local_transport_per_day": 12000, "tour_event_per_day": 10000, "buffer_rate": 0.08},
    "medium": {"meal_per_count": 18000, "lodging_per_night": 100000, "local_transport_per_day": 20000, "tour_event_per_day": 25000, "buffer_rate": 0.10},
    "high":   {"meal_per_count": 30000, "lodging_per_night": 180000, "local_transport_per_day": 35000, "tour_event_per_day": 50000, "buffer_rate": 0.15},
}

LONG_DISTANCE_TRANSPORT = {
    ("서울", "부산"): {"low": 60000, "medium": 120000, "high": 180000},
    ("서울", "제주"): {"low": 120000, "medium": 220000, "high": 350000},
    ("부산", "제주"): {"low": 100000, "medium": 180000, "high": 300000},
}
DEFAULT_LONG_DISTANCE_TRANSPORT = {"low": 50000, "medium": 90000, "high": 150000}

# 좌표(위도, 경도). 출발/목적지 후보 도시 전체. 거리 기반 교통비 차등에 사용.
CITY_COORDS = {
    "서울": (37.5665, 126.9780), "부산": (35.1796, 129.0756), "제주": (33.4996, 126.5312),
    "강릉": (37.7519, 128.8761), "전주": (35.8242, 127.1480), "대구": (35.8714, 128.6014),
    "대전": (36.3504, 127.3845), "광주": (35.1595, 126.8526), "인천": (37.4563, 126.7052),
    "여수": (34.7604, 127.6622), "경주": (35.8562, 129.2247), "속초": (38.2070, 128.5918),
    "춘천": (37.8813, 127.7300),
}
# 제주는 섬 → 항공 프리미엄(명시 테이블에 없는 출발지에서의 기본값).
JEJU_AIR_DEFAULT = {"low": 110000, "medium": 200000, "high": 330000}
# 너무 가까운 구간의 도시 간 이동 최소 비용.
TRANSPORT_FLOOR = {"low": 15000, "medium": 25000, "high": 40000}
# 서울-부산 실거리(약 325km)를 선형 스케일 기준점으로 사용.
SEOUL_BUSAN_KM = 325.0
# 이동수단별 도시 간 교통비 계수. None(미지정)은 1.0과 동일(기존 동작 보존).
TRANSPORT_MODE_COEFF = {"대중교통": 0.7, "기차/KTX": 1.0, "렌터카": 1.1, "자가용": 0.8, "항공": 1.8}


def _haversine_km(a, b):
    lat1, lon1 = a
    lat2, lon2 = b
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    h = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def _intercity_transport(origin, destination, level, transport_mode=None):
    # 명시 테이블이 있으면 그대로 사용(서울-부산/제주, 부산-제주 기존 값 보존).
    explicit = LONG_DISTANCE_TRANSPORT.get((origin, destination)) or LONG_DISTANCE_TRANSPORT.get((destination, origin))
    if explicit:
        return _round_krw(explicit[level] * TRANSPORT_MODE_COEFF.get(transport_mode, 1.0))
    # 제주가 끼면 항공 프리미엄.
    if "제주" in (origin, destination):
        return JEJU_AIR_DEFAULT[level]
    o = CITY_COORDS.get(origin)
    d = CITY_COORDS.get(destination)
    if not o or not d:
        return DEFAULT_LONG_DISTANCE_TRANSPORT[level]
    if origin == destination:
        return TRANSPORT_FLOOR[level]
    km = _haversine_km(o, d)
    # 서울-부산 값을 거리에 선형 비례시켜 목적지별로 차등.
    anchor = LONG_DISTANCE_TRANSPORT[("서울", "부산")][level]
    raw = anchor * km / SEOUL_BUSAN_KM
    coeff = TRANSPORT_MODE_COEFF.get(transport_mode, 1.0)
    return _round_krw(max(raw * coeff, TRANSPORT_FLOOR[level]))


def _safe_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _round_krw(amount):
    return int(round(float(amount) / 1000) * 1000)


def estimate_budget(origin, destination, days, level, people=1, themes=None, companions=None, priority=None, transport_mode=None):
    """예상 경비를 정수(원)로 반환. people 기본 1 → 기존 1인 셈법과 동일."""
    themes = themes or []
    companions = companions or []
    level = str(level or "medium").lower()
    if level not in BUDGET_UNIT_PRICES:
        level = "medium"
    people = max(_safe_int(people, 1), 1)
    days = max(_safe_int(days, 1), 1)

    unit = BUDGET_UNIT_PRICES[level].copy()
    if "activity" in themes:
        unit["tour_event_per_day"] *= 1.5
    if "gourmet" in themes:
        unit["meal_per_count"] *= 1.3
    if "family" in companions:
        unit["buffer_rate"] += 0.05
    if priority == "quality":
        unit["meal_per_count"] *= 1.2

    nights = max(days - 1, 0)
    meal_count = days * 3 - 1 if days > 1 else 2
    rooms = math.ceil(people / 2)

    long_dist = _intercity_transport(origin, destination, level, transport_mode)

    transport = _round_krw((long_dist + unit["local_transport_per_day"] * days) * people)
    lodging = _round_krw(unit["lodging_per_night"] * nights * rooms)
    food = _round_krw(unit["meal_per_count"] * meal_count * people)
    activities = _round_krw(unit["tour_event_per_day"] * days * people)

    subtotal = transport + lodging + food + activities
    buffer = _round_krw(subtotal * unit["buffer_rate"])
    total = _round_krw(subtotal + buffer)

    return {
        "estimated_budget": {
            "transportation": transport,
            "accommodation": lodging,
            "food": food,
            "activities": activities,
            "buffer": buffer,
            "total": total,
        },
        "total": total,
    }
