"""Weather tool.

Wraps the free `Open-Meteo <https://open-meteo.com/>`_ current-conditions API
(no API key required) to fetch weather for each delivery zone. A representative
coordinate per zone is used. Results feed the sidebar's weather/alerts panel and
are passed to the agent as context; they do not alter the solver in v1.

If the API is unreachable the tool returns an empty list rather than raising, so
route planning is never blocked by weather lookups.
"""

from __future__ import annotations

from typing import Any, Dict, List

import requests

from app.core_logger import get_tool_logger

logger = get_tool_logger("weather")

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
_HTTP_TIMEOUT = 10  # seconds

# Minimal WMO weather-code -> description map for readable alerts.
_WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
}


def _describe(code: int) -> str:
    return _WEATHER_CODES.get(int(code), "Unknown")


def get_weather_tool(zones: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Fetch current weather for one representative point per delivery zone.

    Args:
        zones: List of dicts each with ``zone`` (name), ``lat`` and ``lon``.

    Returns:
        One dict per zone with ``zone``, ``temperature_c``, ``wind_speed_kmph``,
        ``precipitation_mm``, ``condition`` (text) and an ``alert`` flag set when
        conditions may affect deliveries (rain/snow/storm/fog/high wind).
    """
    results: List[Dict[str, Any]] = []
    for zone in zones:
        lat, lon = zone.get("lat"), zone.get("lon")
        if lat is None or lon is None:
            continue
        try:
            resp = requests.get(
                OPEN_METEO_URL,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,precipitation,weather_code,wind_speed_10m",
                    "wind_speed_unit": "kmh",
                },
                timeout=_HTTP_TIMEOUT,
            )
            resp.raise_for_status()
            current = resp.json().get("current", {})
            code = current.get("weather_code", 0)
            wind = current.get("wind_speed_10m", 0.0)
            precip = current.get("precipitation", 0.0)
            condition = _describe(code)
            alert = bool(precip and precip > 0) or int(code) >= 45 or (wind and wind > 40)
            results.append(
                {
                    "zone": zone.get("zone"),
                    "temperature_c": current.get("temperature_2m"),
                    "wind_speed_kmph": wind,
                    "precipitation_mm": precip,
                    "condition": condition,
                    "alert": alert,
                }
            )
        except (requests.RequestException, ValueError) as exc:
            logger.warning("Open-Meteo lookup failed for zone %s: %s", zone.get("zone"), exc)
    logger.info("Weather fetched for %d/%d zones", len(results), len(zones))
    return results
