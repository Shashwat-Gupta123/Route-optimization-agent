"""query_alerts_tool — read-only alerts lookup for the chat assistant.

Filters ``alerts.json`` by vehicle_id, severity, type, or acknowledged status.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app import data_access
from app.core_logger import get_tool_logger

logger = get_tool_logger("query_alerts")


def query_alerts_tool(filters: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Filter alerts and return matching records.

    Args:
        filters: Optional dict with any of:
            - ``vehicle_id``   (str): exact match
            - ``severity``     (str): ``info`` | ``warning`` | ``critical``
            - ``type``         (str): e.g. ``eta_deviation``, ``vehicle_breakdown``, …
            - ``acknowledged`` (bool): True → only ack'd; False → only unack'd

    Returns:
        ``{ "count": int, "alerts": [...] }``
    """
    filters = filters or {}
    alerts = data_access.load_alerts()

    vehicle_id = filters.get("vehicle_id")
    severity = filters.get("severity")
    alert_type = filters.get("type")
    acknowledged = filters.get("acknowledged")  # None means "don't filter"

    results: List[Dict[str, Any]] = []
    for a in alerts:
        if vehicle_id and a.get("vehicle_id") != vehicle_id:
            continue
        if severity and a.get("severity") != severity:
            continue
        if alert_type and a.get("type") != alert_type:
            continue
        if acknowledged is not None and bool(a.get("acknowledged")) != bool(acknowledged):
            continue
        results.append(a)

    logger.info("query_alerts_tool: filters=%s → %d matches", filters, len(results))
    return {"count": len(results), "alerts": results}
