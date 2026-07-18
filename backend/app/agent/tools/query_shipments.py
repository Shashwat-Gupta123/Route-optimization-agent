"""query_shipments_tool — read-only shipment lookup for the chat assistant.

Filters ``shipments.json`` by any combination of ``store_id``, ``status``,
``priority``, ``shipment_id``; joins ``stores.json`` so the agent can report
store names and zones without a second tool call.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app import data_access
from app.core_logger import get_tool_logger

logger = get_tool_logger("query_shipments")


def query_shipments_tool(filters: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Filter today's shipments and return matching records.

    Args:
        filters: Optional dict with any of:
            - ``shipment_id`` (str): exact match
            - ``store_id``    (str): exact match
            - ``status``      (str): ``pending`` | ``assigned`` | ``delivered`` | …
            - ``priority``    (str): ``high`` | ``normal`` | ``low``

    Returns:
        ``{ "count": int, "total_weight_kg": float, "shipments": [...] }``
        Each shipment is enriched with its ``store`` sub-object (name, zone, address).
    """
    filters = filters or {}
    shipments = data_access.get_shipments_with_store()

    # Apply each filter key if present in the request
    sid = filters.get("shipment_id")
    store_id = filters.get("store_id")
    status = filters.get("status")
    priority = filters.get("priority")

    results: List[Dict[str, Any]] = []
    for s in shipments:
        if sid and s.get("shipment_id") != sid:
            continue
        if store_id and s.get("store_id") != store_id:
            continue
        if status and s.get("status") != status:
            continue
        if priority and s.get("priority") != priority:
            continue
        results.append(s)

    total_weight = sum(r.get("weight_kg", 0) for r in results)
    logger.info(
        "query_shipments_tool: filters=%s → %d matches (%.1f kg)",
        filters, len(results), total_weight,
    )
    return {
        "count": len(results),
        "total_weight_kg": round(total_weight, 1),
        "shipments": results,
    }
