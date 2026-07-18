"""Re-optimization tool for disrupted routes.

``reoptimize_remaining_tool`` wraps the Component 1 OR-Tools solver
(:func:`optimize_routes_tool`) but changes the depot: instead of starting from
the warehouse, the route starts from the *vehicle's current location*, and only
the stops that have **not** yet been visited (plus any newly injected urgent
orders) are included as demand.

It builds a fresh distance/duration matrix for ``[current_location, *stops]`` via
:func:`get_route_matrix_tool`, runs the solver, and returns the ``balanced``
plan in the same RoutePlan shape Component 1 produces, so the frontend can render
the revised route with the exact same components.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.core_logger import get_tool_logger
from app.agent.tools.route_matrix import get_route_matrix_tool
from app.agent.tools.optimize_routes import optimize_routes_tool

logger = get_tool_logger("reoptimize_remaining")


def reoptimize_remaining_tool(
    start_location: Dict[str, Any],
    unvisited_shipments: List[Dict[str, Any]],
    fleet: List[Dict[str, Any]],
    preferred_plan: str = "balanced",
) -> Dict[str, Any]:
    """Re-solve the remaining stops starting from the vehicle's current position.

    Args:
        start_location: The new depot — the vehicle's current position. Needs
            ``lat``/``lon``; ``id``/``name`` are optional (defaults applied).
        unvisited_shipments: Remaining shipments to serve. Each must carry an
            embedded ``store`` (with ``lat``/``lon``), ``weight_kg`` and the
            delivery-window fields, exactly like the Component 1 pipeline builds.
        fleet: Vehicles available to serve the remaining stops (usually just the
            disrupted vehicle, optionally with spare capacity vehicles).
        preferred_plan: Which of the solver's plans to return as the revised
            route (``fastest`` | ``cheapest`` | ``balanced``).

    Returns:
        ``{"status": "ok", "plan": <RoutePlan dict>}`` on success, or the
        solver's ``{"status": "infeasible", "reason": ...}`` passthrough.
    """
    if not unvisited_shipments:
        return {"status": "infeasible", "reason": "No unvisited stops remain to re-optimize."}
    if not fleet:
        return {"status": "infeasible", "reason": "No vehicle available for re-optimization."}

    # Pseudo-warehouse = the vehicle's current location (the new route start).
    pseudo_warehouse = {
        "warehouse_id": start_location.get("id", "CURRENT_POS"),
        "name": start_location.get("name", "Current Position"),
        "lat": start_location["lat"],
        "lon": start_location["lon"],
        "zone": start_location.get("zone", "Current"),
    }

    # Ordered locations: index 0 = current position, then each unvisited stop.
    locations: List[Dict[str, Any]] = [
        {"store_id": pseudo_warehouse["warehouse_id"], "name": pseudo_warehouse["name"],
         "lat": pseudo_warehouse["lat"], "lon": pseudo_warehouse["lon"]}
    ]
    for s in unvisited_shipments:
        store = s.get("store") or {}
        locations.append(
            {
                "store_id": s["store_id"],
                "name": store.get("store_name"),
                "lat": store.get("lat"),
                "lon": store.get("lon"),
                "address": store.get("address"),
            }
        )

    matrix = get_route_matrix_tool(locations)
    result = optimize_routes_tool(pseudo_warehouse, unvisited_shipments, fleet, matrix)
    if result.get("status") == "infeasible":
        logger.warning("Re-optimization infeasible: %s", result.get("reason"))
        return result

    plans = {p["plan_name"]: p for p in result["plans"]}
    plan = plans.get(preferred_plan) or result["plans"][0]
    logger.info(
        "Re-optimized %d stop(s) from current position (plan=%s)",
        len(unvisited_shipments), plan["plan_name"],
    )
    return {"status": "ok", "plan": plan}
