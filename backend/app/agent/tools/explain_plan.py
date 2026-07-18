"""explain_plan_tool — natural-language explanation of a route plan's decisions.

This tool reasons *about retrieved data* — it does not fetch new information.
Given a plan dict (from query_route_plan_tool), it returns structured facts
about stop ordering, capacity usage, and time-window constraints so the agent
can compose a grounded explanation.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.core_logger import get_tool_logger

logger = get_tool_logger("explain_plan")


def explain_plan_tool(plan: Dict[str, Any]) -> Dict[str, Any]:
    """Extract structured explanatory facts from a route plan dict.

    Args:
        plan: A single plan dict as returned by ``query_route_plan_tool``.

    Returns:
        A structured dict with:
        - ``plan_name``, ``plan_id``, ``status``
        - ``totals``: distance, duration, fuel cost, CO2, on-time %
        - ``routes``: per-vehicle breakdown with stop order + capacity info
        - ``decision_notes``: list of plain-English notes derived purely from
          the plan's own data (capacity %, stop count, priority ordering)
    """
    if not plan:
        return {"error": "No plan provided to explain."}

    plan_name = plan.get("plan_name", "unknown")
    plan_id = plan.get("plan_id", "unknown")
    totals = plan.get("totals", {})
    routes = plan.get("routes", [])

    route_summaries: List[Dict[str, Any]] = []
    decision_notes: List[str] = []

    for route in routes:
        vehicle_id = route.get("vehicle_id", "?")
        stops = route.get("stops", [])
        cap_pct = route.get("capacity_used_pct", 0)
        dist = route.get("distance_km", 0)
        dur = route.get("duration_min", 0)
        fuel = route.get("fuel_cost_inr", 0)

        stop_names = [s.get("store_name") or s.get("store_id") for s in stops]
        priorities = [s.get("priority", "normal") for s in stops]
        high_prio = [n for n, p in zip(stop_names, priorities) if p == "high"]

        route_summaries.append({
            "vehicle_id": vehicle_id,
            "stop_count": len(stops),
            "stop_order": stop_names,
            "capacity_used_pct": cap_pct,
            "distance_km": dist,
            "duration_min": dur,
            "fuel_cost_inr": fuel,
            "high_priority_stops": high_prio,
        })

        # Generate decision notes from plan data only
        if high_prio:
            decision_notes.append(
                f"{vehicle_id} serves {len(high_prio)} high-priority stop(s) first "
                f"({', '.join(high_prio)}) due to narrow time windows."
            )
        if cap_pct > 85:
            decision_notes.append(
                f"{vehicle_id} is running at {cap_pct}% capacity — near maximum load."
            )
        if cap_pct < 40:
            decision_notes.append(
                f"{vehicle_id} is at only {cap_pct}% capacity — consolidation may be possible."
            )
        if len(stops) == 0:
            decision_notes.append(f"{vehicle_id} has no stops assigned in this plan.")

    logger.info("explain_plan_tool: explained plan %s (%s)", plan_id, plan_name)
    return {
        "plan_name": plan_name,
        "plan_id": plan_id,
        "status": plan.get("status", "unknown"),
        "totals": totals,
        "routes": route_summaries,
        "decision_notes": decision_notes,
    }
