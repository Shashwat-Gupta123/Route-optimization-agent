"""query_route_plan_tool — read-only route plan lookup for the chat assistant.

Looks up today's active plan from ``route_plan_sample.json`` or a specific
day in ``route_history.json`` by plan_name, plan_id, or date.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app import data_access
from app.core_logger import get_tool_logger

logger = get_tool_logger("query_route_plan")


def query_route_plan_tool(filters: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Look up a route plan by name, id, or date.

    Args:
        filters: Optional dict with any of:
            - ``plan_name`` (str): ``fastest`` | ``cheapest`` | ``balanced``
            - ``plan_id``   (str): exact plan id
            - ``date``      (str): ``YYYY-MM-DD`` — searches route_history.json
            - ``today``     (bool): if True, always return the current active plan

    Returns:
        ``{ "source": "today" | "history", "plans": [...] }``
        Plans include ``routes``, ``totals``, ``effectiveness_score``, ``status``.
    """
    filters = filters or {}
    plan_name = filters.get("plan_name", "").lower().strip()
    plan_id = filters.get("plan_id", "").strip()
    date_str = filters.get("date", "").strip()
    want_today = filters.get("today", False)

    results: List[Dict[str, Any]] = []
    source: Optional[str] = None

    # Always try today's active plan first (unless only a historical date was requested)
    if not date_str or want_today:
        try:
            plan = data_access.load_route_plan()
            if plan:
                # plan may be a single plan dict or a list of plans
                candidates = plan if isinstance(plan, list) else [plan]
                for p in candidates:
                    if plan_name and p.get("plan_name", "").lower() != plan_name:
                        continue
                    if plan_id and p.get("plan_id") != plan_id:
                        continue
                    results.append(p)
                source = "today"
        except Exception:  # noqa: BLE001
            pass

    # Also search route history when a date is given
    if date_str or (not results and plan_id):
        try:
            history = data_access.load_route_history()
            for record in history:
                if date_str and record.get("date") != date_str:
                    continue
                results.append(record)
                source = "history"
        except Exception:  # noqa: BLE001
            pass

    logger.info(
        "query_route_plan_tool: filters=%s → %d plan(s) from %s",
        filters, len(results), source or "none",
    )
    return {"source": source or "none", "count": len(results), "plans": results}
