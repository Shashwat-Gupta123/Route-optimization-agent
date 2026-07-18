"""compute_kpi_tool — KPI aggregation tool for the chat assistant.

Thin wrapper over the existing analytics_service so the chat agent can
answer questions about on-time %, fuel costs, distance, and weather
correlation without duplicating any logic.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, Optional

from app.core_logger import get_tool_logger

logger = get_tool_logger("compute_kpi")


def _iso_days_ago(n: int) -> str:
    return (date.today() - timedelta(days=n)).isoformat()


def compute_kpi_tool(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    include_weather_correlation: bool = False,
) -> Dict[str, Any]:
    """Return aggregated KPI data for the given date range.

    Args:
        from_date: ISO date string (``YYYY-MM-DD``). Defaults to 7 days ago.
        to_date:   ISO date string (``YYYY-MM-DD``). Defaults to today.
        include_weather_correlation: If True, also return weather-delay data.

    Returns:
        Merged dict from ``analytics_service.summary()`` and optionally
        ``analytics_service.weather_correlation()``.
    """
    # Lazy import to avoid circular imports at module load time
    from app.agent import analytics_service  # noqa: PLC0415

    from_date = from_date or _iso_days_ago(7)
    to_date = to_date or date.today().isoformat()

    try:
        summary = analytics_service.summary(from_date, to_date)
    except ValueError as exc:
        logger.warning("compute_kpi_tool: summary failed: %s", exc)
        summary = {"error": str(exc)}

    result: Dict[str, Any] = {"from_date": from_date, "to_date": to_date, **summary}

    if include_weather_correlation:
        try:
            result["weather_correlation"] = analytics_service.weather_correlation()
        except Exception as exc:  # noqa: BLE001
            logger.warning("compute_kpi_tool: weather_correlation failed: %s", exc)

    logger.info("compute_kpi_tool: %s → %s", from_date, to_date)
    return result
