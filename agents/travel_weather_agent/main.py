import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode

try:
    import requests
except ImportError:  # pragma: no cover - environment safety fallback
    requests = None

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - environment safety fallback
    load_dotenv = None


KMA_FORECAST_URL = (
    "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
)
LOCATION_GRIDS = {
    "서울": {"nx": 60, "ny": 127},
    "부산": {"nx": 98, "ny": 76},
    "제주": {"nx": 52, "ny": 38},
    "인천": {"nx": 55, "ny": 124},
    "대구": {"nx": 89, "ny": 90},
    "대전": {"nx": 67, "ny": 100},
    "광주": {"nx": 58, "ny": 74},
    "울산": {"nx": 102, "ny": 84},
    "세종": {"nx": 66, "ny": 103},
    "강릉": {"nx": 92, "ny": 131},
    "전주": {"nx": 63, "ny": 89},
    "여수": {"nx": 73, "ny": 66},
    "경주": {"nx": 100, "ny": 91},
    "속초": {"nx": 87, "ny": 141},
    "춘천": {"nx": 73, "ny": 134}
}


def _as_input_dict(input_data):
    return input_data if isinstance(input_data, dict) else {}


def _get_trip_context(input_data, default_location=None):
    safe_input = _as_input_dict(input_data)
    user_request = str(safe_input.get("user_request") or "")
    request_location = next(
        (location_name for location_name in LOCATION_GRIDS if location_name in user_request),
        None
    )
    location = (
        safe_input.get("location")
        or safe_input.get("destination")
        or request_location
        or default_location
        or "서울"
    )
    try:
        days = int(safe_input.get("days", safe_input.get("duration_days", 3)))
    except (TypeError, ValueError):
        days = 3
    period = safe_input.get("period", f"{days}일 여행")
    season = safe_input.get("season", "any")
    return safe_input, location, days, period, season


def _grid_for_location(location):
    return LOCATION_GRIDS.get(location, LOCATION_GRIDS["서울"])


def load_service_key():
    """Load KMA service key from .env if python-dotenv is available."""
    if load_dotenv is not None:
        env_path = Path(__file__).with_name(".env")
        load_dotenv(dotenv_path=env_path)

    return os.getenv("KMA_SERVICE_KEY")


def _build_debug_info(service_key=None, base_date=None, base_time=None, location="서울", data_source=None, debug_message=None, days=None):
    if base_date is None or base_time is None:
        base_date, base_time = _get_kma_base_datetime()

    key_loaded = bool(service_key)
    grid = _grid_for_location(location)
    request_params = {
        "pageNo": 1,
        "numOfRows": 1000,
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": grid["nx"],
        "ny": grid["ny"]
    }
    clean_params = {
        key: value
        for key, value in request_params.items()
        if value is not None
    }

    return {
        "key_loaded": key_loaded,
        "key_length": len(service_key) if service_key else 0,
        "key_preview": f"{service_key[:4]}..." if service_key else None,
        "request_url_without_service_key": (
            f"{KMA_FORECAST_URL}?{urlencode(clean_params)}"
        ),
        "location": location,
        "base_date": base_date,
        "base_time": base_time,
        "nx": grid["nx"],
        "ny": grid["ny"],
        "days": days,
        "data_source": data_source,
        "debug_message": debug_message
    }


def _safe_error_message(exc, service_key=None):
    message = f"{type(exc).__name__}: {exc}"
    if service_key:
        message = message.replace(service_key, "[redacted_service_key]")
    return message


def _get_kma_base_datetime(now=None):
    """Return a conservative KMA base date/time for short-term forecasts."""
    now = now or datetime.now()
    forecast_times = ["0200", "0500", "0800", "1100", "1400", "1700", "2000", "2300"]
    safe_now = now - timedelta(minutes=30)
    current_hhmm = safe_now.strftime("%H%M")

    available_times = [base_time for base_time in forecast_times if base_time <= current_hhmm]
    if available_times:
        return safe_now.strftime("%Y%m%d"), available_times[-1]

    previous_day = safe_now - timedelta(days=1)
    return previous_day.strftime("%Y%m%d"), "2300"


def _translate_condition(sky_code=None, pty_code=None):
    precipitation = {
        "1": "비",
        "2": "비 또는 눈",
        "3": "눈",
        "4": "소나기"
    }
    sky = {
        "1": "맑음",
        "3": "구름 많음",
        "4": "흐림"
    }

    if pty_code in precipitation:
        return precipitation[pty_code]
    return sky.get(sky_code, "예보 정보 확인 필요")


def _parse_kma_items(items):
    # 날짜별 데이터 그룹화
    daily_raw = {}
    for item in items:
        date = item.get("fcstDate")
        category = item.get("category")
        value = item.get("fcstValue")
        
        if date not in daily_raw:
            daily_raw[date] = {}
        
        if category in {"TMP", "SKY", "PTY", "POP"}:
            # 하루 중 여러 시간대 데이터가 있으므로, 특정 시간대(예: 낮 12시 근처)를 우선하거나 평균적인 값을 취할 수 있음
            # 여기서는 단순화를 위해 해당 날짜의 첫 번째(또는 대표) 값을 유지
            if category not in daily_raw[date]:
                daily_raw[date][category] = value

    parsed_days = []
    # 날짜순 정렬하여 결과 생성
    for date in sorted(daily_raw.keys()):
        d = daily_raw[date]
        parsed_days.append({
            "date": f"{date[4:6]}.{date[6:8]}",
            "temperature": f"{d.get('TMP', '확인 필요')}°C",
            "condition": _translate_condition(d.get("SKY"), d.get("PTY")),
            "rain_probability": f"{d.get('POP', '확인 필요')}%"
        })
    
    return parsed_days


def fetch_kma_forecast(input_data, service_key):
    """Fetch a best-effort KMA forecast with safe debug details."""
    base_date, base_time = _get_kma_base_datetime()
    _safe_input, location, days, period, _season = _get_trip_context(
        input_data,
        default_location="서울"
    )
    grid = _grid_for_location(location)
    debug_info = _build_debug_info(
        service_key,
        base_date,
        base_time,
        location=location,
        data_source="mock_fallback",
        debug_message="not_called",
        days=days
    )

    if requests is None:
        return None, "missing_dependency: requests", _build_debug_info(service_key, base_date, base_time, location=location, data_source="mock_fallback", debug_message="missing_dependency: requests", days=days)
    if not service_key:
        return None, "missing_service_key", _build_debug_info(service_key, base_date, base_time, location=location, data_source="mock_fallback", debug_message="missing_service_key", days=days)

    try:
        params = {
            "serviceKey": service_key,
            "pageNo": 1,
            "numOfRows": 1000,
            "dataType": "JSON",
            "base_date": base_date,
            "base_time": base_time,
            "nx": grid["nx"],
            "ny": grid["ny"]
        }
        response = requests.get(KMA_FORECAST_URL, params=params, timeout=5)
        if response.status_code >= 400:
            message = f"http_error: {response.status_code}"
            return None, message, _build_debug_info(service_key, base_date, base_time, location=location, data_source="mock_fallback", debug_message=message, days=days)

        try:
            payload = response.json()
        except ValueError:
            message = f"parse_error: json_decode_failed: {response.text[:300]}"
            return (
                None,
                message,
                _build_debug_info(service_key, base_date, base_time, location=location, data_source="mock_fallback", debug_message=message, days=days)
            )

        response_body = payload.get("response", {})
        header = response_body.get("header", {})
        if header.get("resultCode") != "00":
            result_code = header.get("resultCode", "unknown")
            result_msg = header.get("resultMsg", "unknown")
            message = f"api_result_error: resultCode={result_code}, resultMsg={result_msg}"
            return (
                None,
                message,
                _build_debug_info(service_key, base_date, base_time, location=location, data_source="mock_fallback", debug_message=message, days=days)
            )

        items = (
            response_body
            .get("body", {})
            .get("items", {})
            .get("item", [])
        )
        if not isinstance(items, list) or not items:
            return None, "empty_items", _build_debug_info(service_key, base_date, base_time, location=location, data_source="mock_fallback", debug_message="empty_items", days=days)

        try:
            daily_weather = _parse_kma_items(items)
        except Exception as exc:
            message = f"parse_error: {_safe_error_message(exc, service_key)}"
            return None, message, _build_debug_info(service_key, base_date, base_time, location=location, data_source="mock_fallback", debug_message=message, days=days)
        
        # 기상청 데이터가 부족할 경우 "추후 업데이트"로 보충
        final_daily = []
        start_dt = datetime.now()
        for i in range(days):
            current_date_str = (start_dt + timedelta(days=i)).strftime("%m.%d")
            found = next((d for d in daily_weather if d["date"] == current_date_str), None)
            if found:
                final_daily.append(found)
            else:
                final_daily.append({
                    "date": current_date_str,
                    "temperature": "추후 업데이트",
                    "condition": "예보 준비 중",
                    "rain_probability": "추후 업데이트"
                })

        debug_info = _build_debug_info(
            service_key,
            base_date,
            base_time,
            location=location,
            data_source="kma_api",
            debug_message="kma_api_success",
            days=days
        )
        
        primary = final_daily[0]
        forecast = {
            "location": location,
            "period": period,
            "temperature": primary["temperature"],
            "condition": primary["condition"],
            "rain_probability": primary["rain_probability"],
            "daily_forecast": final_daily
        }

        return {
            "agent": "travel_weather_agent",
            "summary": (
                f"KMA short-term forecast was checked for {location} for {days} days."
            ),
            "location": location,
            "forecast": forecast,
            "weather_summary": forecast,
            "weather": forecast,
            "daily_forecast": final_daily,
            "weather_findings": [
                "기상청 단기예보 API 응답에서 가능한 항목만 추출했습니다.",
                f"{location} 기준 격자 좌표(nx={grid['nx']}, ny={grid['ny']})를 사용했습니다.",
                f"조회 기준 시각은 {base_date} {base_time}입니다."
            ],
            "recommendations": [
                "출발 직전 최신 예보를 다시 확인하세요.",
                "비 가능성이 있으면 접이식 우산과 방수 가능한 신발을 준비하세요.",
                "야외 일정은 예보 변동에 따라 실내 일정으로 바꿀 수 있게 구성하세요."
            ],
            "risks": [
                "현재 단계의 API 파싱은 제한적이므로 일부 예보 항목이 누락될 수 있습니다.",
                "기상청 응답 지연 또는 키 오류가 있으면 mock fallback으로 전환됩니다.",
                "실제 여행지와 서울 기준 예보가 다를 수 있습니다."
            ],
            "next_agents": [
                "travel_schedule_agent",
                "travel_budget_agent",
                "packing_checklist_agent"
            ],
            "data_source": "kma_api",
            "debug_message": "kma_api_success",
            "debug_info": debug_info
        }, None, debug_info
    except requests.exceptions.RequestException as exc:
        message = f"request_exception: {_safe_error_message(exc, service_key)}"
        return None, message, _build_debug_info(service_key, base_date, base_time, location=location, data_source="mock_fallback", debug_message=message, days=days)
    except Exception as exc:
        message = f"parse_error: {_safe_error_message(exc, service_key)}"
        return None, message, _build_debug_info(service_key, base_date, base_time, location=location, data_source="mock_fallback", debug_message=message, days=days)


def build_mock_weather_result(input_data, debug_message="mock_fallback", debug_info=None):
    """Return mock travel weather data without calling public APIs."""
    _safe_input, location, days, period, season = _get_trip_context(input_data)

    if season == "summer":
        temperature = "26-32°C"
        condition = "덥고 습한 날씨"
        rain_probability = "45%"
    elif season == "winter":
        temperature = "0-8°C"
        condition = "쌀쌀하고 건조한 날씨"
        rain_probability = "20%"
    else:
        temperature = "18-25°C"
        condition = "대체로 맑고 선선한 날씨"
        rain_probability = "30%"

    debug_info = debug_info or _build_debug_info(
        location=location,
        data_source="mock_fallback",
        debug_message=debug_message,
        days=days
    )
    debug_info.update({
        "location": location,
        "days": days,
        "data_source": "mock_fallback",
        "debug_message": debug_message
    })

    # Mock 전일 날씨 생성
    final_daily = []
    start_dt = datetime.now()
    for i in range(days):
        current_date_str = (start_dt + timedelta(days=i)).strftime("%m.%d")
        final_daily.append({
            "date": current_date_str,
            "temperature": temperature,
            "condition": condition,
            "rain_probability": rain_probability
        })

    forecast = {
        "location": location,
        "period": period,
        "temperature": temperature,
        "condition": condition,
        "rain_probability": rain_probability,
        "daily_forecast": final_daily
    }

    return {
        "agent": "travel_weather_agent",
        "summary": (
            f"Mock weather estimate for {location} for {days} days. "
            f"No public weather API was called."
        ),
        "location": location,
        "forecast": forecast,
        "weather_summary": forecast,
        "weather": forecast,
        "daily_forecast": final_daily,
        "weather_findings": [
            "여행 기간 중 실외 활동이 가능한 수준의 날씨로 가정했습니다.",
            "비 가능성은 mock 값이며 실제 예보와 다를 수 있습니다.",
            "기온은 하루 평균 체감 범위를 단순화한 예시입니다."
        ],
        "recommendations": [
            "가벼운 겉옷과 접이식 우산을 준비하는 것이 좋습니다.",
            "야외 일정은 오전이나 늦은 오후에 배치하면 이동 피로를 줄일 수 있습니다.",
            "비 예보가 있는 날에는 실내 관광지를 대체 코스로 준비하세요."
        ],
        "risks": [
            "실제 날씨는 출발 전 최신 예보로 다시 확인해야 합니다.",
            "강풍이나 폭우가 있으면 교통 지연이 발생할 수 있습니다.",
            "기온 차가 큰 지역은 야간 활동 시 체감 온도가 낮을 수 있습니다."
        ],
        "next_agents": [
            "travel_schedule_agent",
            "travel_budget_agent",
            "packing_checklist_agent"
        ],
        "data_source": "mock_fallback",
        "debug_message": debug_message,
        "debug_info": debug_info
    }


def run(input_data):
    """Return KMA weather data when available, otherwise keep mock fallback stable."""
    safe_input = _as_input_dict(input_data)
    _safe_input, location, days, _period, _season = _get_trip_context(safe_input, default_location="서울")
    debug_message = "missing_service_key"
    debug_info = _build_debug_info(location=location, data_source="mock_fallback", debug_message=debug_message, days=days)
    try:
        service_key = load_service_key()
        debug_info = _build_debug_info(service_key, location=location, data_source="mock_fallback", debug_message=debug_message, days=days)
        if service_key:
            kma_result, debug_message, debug_info = fetch_kma_forecast(
                safe_input,
                service_key
            )
            if kma_result:
                return kma_result
        else:
            debug_message = "missing_service_key"
    except Exception:
        debug_message = "parse_error: unexpected_run_error"

    return build_mock_weather_result(safe_input, debug_message, debug_info)


if __name__ == "__main__":
    sample_input = {
        "destination": "제주",
        "location": "제주",
        "origin": "서울",
        "days": 3
    }
    print(json.dumps(run(sample_input), ensure_ascii=False, indent=2))
