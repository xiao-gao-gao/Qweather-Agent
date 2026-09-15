"""和风天气查询工具。

环境变量：
    WEATHER_API_KEY: 和风天气 API KEY 凭据
    WEATHER_API_HOST: 控制台“设置”中的专属 API Host
"""

from __future__ import annotations

import json
import os
from typing import Any

import dotenv
import requests


dotenv.load_dotenv()

REQUEST_TIMEOUT = 8


def _json(data: dict[str, Any]) -> str:
    """以适合直接返回给大模型工具调用的格式序列化结果。"""
    return json.dumps(data, ensure_ascii=False)


def _settings() -> tuple[str | None, str | None]:
    """动态读取配置，便于修改环境变量后立即生效。"""
    api_key = os.getenv("WEATHER_API_KEY")
    api_host = os.getenv("WEATHER_API_HOST")
    if api_host:
        api_host = api_host.strip().removeprefix("https://").removeprefix("http://").rstrip("/")
    return api_key, api_host


def _request(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    api_key, api_host = _settings()
    if not api_key:
        raise RuntimeError("缺少环境变量 WEATHER_API_KEY")
    if not api_host:
        raise RuntimeError("缺少环境变量 WEATHER_API_HOST（请填写控制台中的专属 API Host）")

    response = requests.get(
        f"https://{api_host}{path}",
        params=params,
        headers={"X-QW-Api-Key": api_key, "Accept-Encoding": "gzip"},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def _lookup_location(city_name: str) -> dict[str, Any]:
    city_name = city_name.strip()
    if not city_name:
        raise ValueError("城市名称不能为空")

    data = _request(
        "/geo/v2/city/lookup",
        {"location": city_name, "range": "cn", "number": 1, "lang": "zh"},
    )
    locations = data.get("location") or []
    if data.get("code") != "200" or not locations:
        raise LookupError(f"未找到城市：{city_name}（API 状态码：{data.get('code', '未知')}）")
    return locations[0]


def get_location_id(city_name: str) -> str | None:
    """查询城市的 Location ID；查询失败时返回 ``None``。"""
    try:
        return str(_lookup_location(city_name)["id"])
    except (KeyError, LookupError, RuntimeError, ValueError, requests.RequestException):
        return None


def _error(exc: Exception) -> str:
    if isinstance(exc, requests.Timeout):
        message = "天气服务请求超时，请稍后重试"
    elif isinstance(exc, requests.HTTPError):
        status = exc.response.status_code if exc.response is not None else "未知"
        message = f"天气服务 HTTP 请求失败（状态码：{status}）"
    elif isinstance(exc, requests.RequestException):
        message = f"无法连接天气服务：{exc}"
    elif isinstance(exc, (json.JSONDecodeError, ValueError)) and not isinstance(exc, RuntimeError):
        message = str(exc) or "天气服务返回了无效数据"
    else:
        message = str(exc)
    return _json({"success": False, "error": message})


def get_daily_weather(city_name: str, days: int = 3) -> str:
    """查询中国城市未来 1～10 天的每日天气预报。"""
    if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 10:
        return _json({"success": False, "error": "days 必须是 1 到 10 之间的整数"})

    try:
        location = _lookup_location(city_name)
        latitude = round(float(location["lat"]), 2)
        longitude = round(float(location["lon"]), 2)
        data = _request(
            f"/weather/v1/daily/{latitude:.2f}/{longitude:.2f}",
            {"days": days, "localTime": "true", "lang": "zh"},
        )
        forecasts = data.get("days")
        if not isinstance(forecasts, list):
            raise RuntimeError("天气服务未返回每日预报数据")

        result_days = []
        for item in forecasts:
            daytime = item.get("daytime") or {}
            nighttime = item.get("nighttime") or {}
            precipitation = daytime.get("precipitation") or {}
            result_days.append(
                {
                    "date": (item.get("forecastStartTime") or "")[:10],
                    "tempMax": (item.get("temperatureMax") or {}).get("value"),
                    "tempMin": (item.get("temperatureMin") or {}).get("value"),
                    "tempUnit": (item.get("temperatureMax") or {}).get("unit", "°C"),
                    "dayText": (daytime.get("condition") or {}).get("text"),
                    "nightText": (nighttime.get("condition") or {}).get("text"),
                    "dayWindScale": (daytime.get("wind") or {}).get("scale"),
                    "precipitationProbability": precipitation.get("probability"),
                    "humidity": daytime.get("humidity"),
                    "sunrise": (item.get("astro") or {}).get("sunrise"),
                    "sunset": (item.get("astro") or {}).get("sunset"),
                }
            )

        return _json(
            {
                "success": True,
                "city": location.get("name", city_name),
                "adm1": location.get("adm1"),
                "adm2": location.get("adm2"),
                "forecast": result_days,
                "attributions": (data.get("metadata") or {}).get("attributions", []),
            }
        )
    except (KeyError, TypeError, LookupError, RuntimeError, ValueError, requests.RequestException) as exc:
        return _error(exc)