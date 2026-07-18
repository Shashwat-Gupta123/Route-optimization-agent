"""Route planning orchestration service.

Coordinates the deterministic planning pipeline that powers ``/api/plan-routes``:

    build locations  ->  get_route_matrix_tool  ->  get_weather_tool
                     ->  optimize_routes_tool   ->  cache + summarise

The tool functions here are the *same* ones registered with the MAF agent in
:mod:`app.agent.route_planner_agent`; the pipeline calls them directly so route
computation is fast and deterministic (no large matrices routed through the LLM),
while the agent adds the natural-language layer (plan summary and ``/api/ask``).

Generated plans are held in a small in-memory cache keyed by ``plan_id`` so the
approve and ask endpoints can retrieve them without recomputing.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from app import data_access
from app.core_logger import get_logger
from app.agent import route_planner_agent
from app.agent.tools.route_matrix import get_route_matrix_tool
from app.agent.tools.weather import get_weather_tool
from app.agent.tools.optimize_routes import optimize_routes_tool

logger = get_logger("service")

_IST = timezone(timedelta(hours=5, minutes=30))

# In-memory cache of the most recently generated plans: plan_id -> plan dict.
_plan_cache: Dict[str, Dict[str, Any]] = {}
_cache_lock = threading.Lock()


class InfeasiblePlanError(Exception):
    """Raised when the solver cannot satisfy the capacity/time-window constraints."""


def _make_plan_id(plan_name: str, seq: int) -> str:
    today = datetime.now(_IST).strftime("%Y-%m-%d")
    return f"PLAN-{today}-{seq:03d}-{plan_name}"


def _cache_plans(plans: List[Dict[str, Any]]) -> None:
    with _cache_lock:
        for plan in plans:
            _plan_cache[plan["plan_id"]] = plan


def get_cached_plan(plan_id: str) -> Optional[Dict[str, Any]]:
    with _cache_lock:
        return _plan_cache.get(plan_id)


async def plan_routes() -> Dict[str, Any]:
    """Run the full planning pipeline and return plans + weather + summary.

    Raises:
        InfeasiblePlanError: if no plan satisfies the constraints (mapped to a
            422 response by the API layer).
    """
    warehouse = data_access.load_warehouse()
    shipments = [
        s for s in data_access.get_shipments_with_store()
        if s.get("status") in (None, "pending")
    ]
    fleet = data_access.get_available_fleet()

    if not shipments:
        raise InfeasiblePlanError("No pending shipments to plan for today.")
    if not fleet:
        raise InfeasiblePlanError("No vehicles are currently available.")

    # 1) Build the ordered location list (warehouse at index 0).
    locations: List[Dict[str, Any]] = [
        {"store_id": warehouse["warehouse_id"], "name": warehouse.get("name"),
         "lat": warehouse["lat"], "lon": warehouse["lon"]}
    ]
    for s in shipments:
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

    # 2) Distance/duration matrix (ORS with haversine fallback).
    matrix = get_route_matrix_tool(locations)

    # 3) Weather for each unique delivery zone (+ warehouse zone).
    zones = _unique_zones(warehouse, shipments)
    weather = get_weather_tool(zones)

    # 4) Optimize -> three plans.
    result = optimize_routes_tool(warehouse, shipments, fleet, matrix)
    if result.get("status") == "infeasible":
        raise InfeasiblePlanError(result.get("reason", "Route planning is infeasible."))

    plans = result["plans"]
    for i, plan in enumerate(plans, start=1):
        plan["plan_id"] = _make_plan_id(plan["plan_name"], i)
    _cache_plans(plans)

    # 5) Natural-language trade-off summary (best-effort).
    summary = await route_planner_agent.summarize_plans(plans)

    return {"plans": plans, "weather": weather, "summary": summary}


def _unique_zones(
    warehouse: Dict[str, Any], shipments: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """One representative coordinate per delivery zone (for weather lookups)."""
    seen: Dict[str, Dict[str, Any]] = {}
    wh_zone = warehouse.get("zone", "Warehouse")
    seen[wh_zone] = {"zone": wh_zone, "lat": warehouse["lat"], "lon": warehouse["lon"]}
    for s in shipments:
        store = s.get("store") or {}
        zone = store.get("zone")
        if zone and zone not in seen:
            seen[zone] = {"zone": zone, "lat": store.get("lat"), "lon": store.get("lon")}
    return list(seen.values())


def approve_route(plan_id: str) -> Dict[str, Any]:
    """Persist the selected plan and mark its shipments as assigned.

    Writes the approved plan to ``route_plan_sample.json`` and updates the
    matching shipments in ``shipments.json``.
    """
    plan = get_cached_plan(plan_id)
    if plan is None:
        raise KeyError(plan_id)

    approved = dict(plan)
    approved["status"] = "approved"
    approved["approved_at"] = datetime.now(_IST).replace(microsecond=0).isoformat()
    approved["approved_by"] = "Warehouse Dispatch Manager"

    data_access.save_route_plan(approved)

    assignments: Dict[str, str] = {}
    for route in plan["routes"]:
        for stop in route["stops"]:
            assignments[stop["shipment_id"]] = route["vehicle_id"]
    data_access.update_shipment_assignments(plan_id, assignments)

    logger.info("Approved plan %s (%d shipments assigned)", plan_id, len(assignments))
    return approved


async def ask(question: str, plan_id: Optional[str]) -> str:
    """Answer a free-text question about a plan via the MAF agent."""
    plan = get_cached_plan(plan_id) if plan_id else None
    return await route_planner_agent.answer_question(question, plan)
