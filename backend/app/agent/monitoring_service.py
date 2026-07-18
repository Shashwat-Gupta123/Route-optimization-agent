"""Real-time monitoring & disruption-handling service (Component 2).

Thin orchestration layer between the monitoring API router and the Component 2
tools. Mirrors the structure of :mod:`app.agent.service` (Component 1): the
router stays a thin FastAPI shell, while this module coordinates the data-access
layer and the three monitoring tools (``detect_eta_deviation_tool``,
``reoptimize_remaining_tool``, ``send_alert_tool``).

Demo mode: vehicle positions come from ``vehicle_locations.json`` (treated like a
live GPS feed) and disruptions are triggered from the UI rather than detected
from real telematics.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from app import data_access
from app.config import get_config
from app.core_logger import get_logger
from app.agent.tools.route_matrix import get_route_matrix_tool
from app.agent.tools.detect_eta_deviation import detect_eta_deviation_tool
from app.agent.tools.reoptimize_remaining import reoptimize_remaining_tool
from app.agent.tools.send_alert import send_alert_tool

logger = get_logger("monitoring")

_IST = timezone(timedelta(hours=5, minutes=30))

# In-memory cache of re-optimization previews awaiting confirmation.
_reopt_cache: Dict[str, Dict[str, Any]] = {}
_cache_lock = threading.Lock()


def _now_ist_iso() -> str:
    return datetime.now(_IST).replace(microsecond=0).isoformat()


def _threshold_min() -> int:
    return int(get_config().get("alerting", {}).get("eta_deviation_threshold_min", 10))


# --- Vehicle locations -------------------------------------------------------

def get_vehicle_locations() -> Dict[str, Any]:
    """Return the live-feed positions enriched with driver + next-stop names."""
    feed = data_access.load_vehicle_locations()
    stores = data_access.get_stores_by_id()
    vehicles_meta = data_access.get_vehicles_by_id()
    drivers = data_access.get_drivers_by_id()

    enriched: List[Dict[str, Any]] = []
    for v in feed.get("vehicles", []):
        meta = vehicles_meta.get(v["vehicle_id"], {})
        driver = drivers.get(meta.get("assigned_driver_id"), {})
        next_store = stores.get(v.get("next_stop"), {})
        item = dict(v)
        item["driver_name"] = driver.get("name")
        item["vehicle_type"] = meta.get("type")
        item["next_stop_name"] = next_store.get("store_name")
        enriched.append(item)
    return {"last_updated": feed.get("last_updated"), "vehicles": enriched}


def _vehicle_location(vehicle_id: str) -> Optional[Dict[str, Any]]:
    for v in data_access.load_vehicle_locations().get("vehicles", []):
        if v.get("vehicle_id") == vehicle_id:
            return v
    return None


def _vehicle_with_driver(vehicle_id: str) -> Optional[Dict[str, Any]]:
    """Build a fleet-payload record (vehicle + joined driver) for the solver."""
    vehicle = data_access.get_vehicles_by_id().get(vehicle_id)
    if vehicle is None:
        return None
    merged = dict(vehicle)
    merged["driver"] = data_access.get_drivers_by_id().get(vehicle.get("assigned_driver_id"))
    return merged


# --- Disruption simulation ---------------------------------------------------

def simulate_traffic_jam(vehicle_id: str, delay_min: float) -> Dict[str, Any]:
    """Add an ETA delay to a vehicle and alert if it breaches the threshold."""
    vehicle = _vehicle_location(vehicle_id)
    if vehicle is None:
        raise KeyError(vehicle_id)

    new_deviation = float(vehicle.get("eta_deviation_min") or 0.0) + float(delay_min)
    updated = data_access.update_vehicle_location(
        vehicle_id,
        {"eta_deviation_min": round(new_deviation, 1), "status": "delayed"},
    )

    stores = data_access.get_stores_by_id()
    next_store = stores.get(updated.get("next_stop")) if updated else None
    next_loc = (
        {"lat": next_store["lat"], "lon": next_store["lon"]} if next_store else None
    )
    detection = detect_eta_deviation_tool(updated, next_loc)

    alert = None
    if detection["exceeds_threshold"]:
        store_name = next_store.get("store_name") if next_store else updated.get("next_stop")
        alert = send_alert_tool(
            alert_type="eta_deviation",
            severity="warning",
            message=(
                f"Vehicle {vehicle_id} is running {detection['eta_deviation_min']:.0f} min "
                f"behind ETA to {store_name}. Revised ETA {detection['revised_eta']}."
            ),
            channel=["email", "dashboard"],
            vehicle_id=vehicle_id,
        )
    return {
        "status": "ok",
        "message": f"Traffic jam simulated for {vehicle_id} (+{delay_min:.0f} min).",
        "vehicle": updated,
        "alert": alert,
        "detection": detection,
    }


def simulate_breakdown(vehicle_id: str) -> Dict[str, Any]:
    """Mark a vehicle broken down, flag its shipments, raise a critical alert."""
    vehicle = _vehicle_location(vehicle_id)
    if vehicle is None:
        raise KeyError(vehicle_id)

    updated = data_access.update_vehicle_location(
        vehicle_id, {"status": "breakdown", "current_speed_kmph": 0}
    )
    affected = data_access.flag_shipments_for_reassignment(vehicle_id)

    alert = send_alert_tool(
        alert_type="vehicle_breakdown",
        severity="critical",
        message=(
            f"Vehicle {vehicle_id} has broken down. "
            f"{len(affected)} shipment(s) need reassignment: {', '.join(affected) or 'none'}."
        ),
        channel=["email", "dashboard"],
        vehicle_id=vehicle_id,
    )
    return {
        "status": "ok",
        "message": f"Breakdown simulated for {vehicle_id}.",
        "vehicle": updated,
        "alert": alert,
        "affected_shipment_ids": affected,
    }


def add_urgent_order(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Inject a new pending shipment for the next re-optimization run."""
    warehouse = data_access.load_warehouse()
    shipment_id = _next_shipment_id()
    shipment = {
        "shipment_id": shipment_id,
        "store_id": fields["store_id"],
        "warehouse_id": warehouse.get("warehouse_id"),
        "order_date": datetime.now(_IST).strftime("%Y-%m-%d"),
        "created_at": _now_ist_iso(),
        "items": [],
        "weight_kg": float(fields["weight_kg"]),
        "volume_m3": float(fields.get("volume_m3", 0.0)),
        "earliest_delivery_time": fields.get("earliest_delivery_time", "00:00"),
        "latest_delivery_time": fields["latest_delivery_time"],
        "priority": fields.get("priority", "high"),
        "special_handling": bool(fields.get("special_handling", False)),
        "status": "pending",
        "assigned_plan_id": None,
        "assigned_vehicle_id": None,
    }
    data_access.add_shipment(shipment)

    alert = send_alert_tool(
        alert_type="urgent_order",
        severity="info",
        message=(
            f"Urgent order {shipment_id} added for store {fields['store_id']} "
            f"({shipment['weight_kg']:.0f} kg, deadline {shipment['latest_delivery_time']})."
        ),
        channel=["dashboard"],
        shipment_id=shipment_id,
    )
    return {
        "status": "ok",
        "message": f"Urgent order {shipment_id} added to the pending pool.",
        "alert": alert,
        "shipment": shipment,
    }


def _next_shipment_id() -> str:
    max_num = 1000
    for s in data_access.load_shipments():
        sid = str(s.get("shipment_id", ""))
        digits = "".join(ch for ch in sid if ch.isdigit())
        if digits:
            max_num = max(max_num, int(digits))
    return f"SHP{max_num + 1}"


# --- Alerts ------------------------------------------------------------------

def list_alerts() -> List[Dict[str, Any]]:
    """Return alerts, most recent first."""
    alerts = data_access.load_alerts()
    return sorted(alerts, key=lambda a: a.get("created_at", ""), reverse=True)


def acknowledge_alert(alert_id: str) -> Dict[str, Any]:
    alert = data_access.acknowledge_alert(alert_id)
    if alert is None:
        raise KeyError(alert_id)
    return alert


# --- Re-optimization ---------------------------------------------------------

def _remaining_shipments_for_vehicle(
    vehicle_id: str, plan: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Unvisited stops for a vehicle in the approved plan, as shipment records.

    Uses the live feed's ``last_stop_completed`` to drop already-delivered stops,
    then joins the remaining stops back to full shipment records (+ store)."""
    route = next((r for r in plan.get("routes", []) if r.get("vehicle_id") == vehicle_id), None)
    if route is None:
        return []

    loc = _vehicle_location(vehicle_id) or {}
    last_done = loc.get("last_stop_completed")

    stop_store_ids = [s["store_id"] for s in route.get("stops", [])]
    if last_done and last_done in stop_store_ids:
        remaining_ids = stop_store_ids[stop_store_ids.index(last_done) + 1:]
    else:
        remaining_ids = stop_store_ids

    shipments_by_store = {
        s["store_id"]: s for s in data_access.get_shipments_with_store()
    }
    # Genuinely new urgent orders = pending shipments whose store is not part of
    # the approved plan at all (an urgent order injected after planning).
    planned_store_ids = {
        st["store_id"] for r in plan.get("routes", []) for st in r.get("stops", [])
    }
    pending_urgent = [
        s for s in data_access.get_shipments_with_store()
        if s.get("status") == "pending" and s["store_id"] not in planned_store_ids
    ]

    remaining: List[Dict[str, Any]] = []
    for store_id in remaining_ids:
        ship = shipments_by_store.get(store_id)
        if ship:
            remaining.append(ship)
    remaining.extend(pending_urgent)
    return remaining


def _route_metrics_for_order(
    start_location: Dict[str, float], ordered_shipments: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Distance/duration for serving stops in the given order from a start point.

    Builds a matrix over ``[start, *stops]`` and sums the sequential legs plus the
    return leg to the start, giving a like-for-like comparison against the
    re-optimized plan (which also returns to its start depot)."""
    locations = [{"store_id": "START", "lat": start_location["lat"], "lon": start_location["lon"]}]
    affected: List[str] = []
    for s in ordered_shipments:
        store = s.get("store") or {}
        locations.append({"store_id": s["store_id"], "lat": store.get("lat"), "lon": store.get("lon")})
        affected.append(store.get("store_name", s["store_id"]))

    matrix = get_route_matrix_tool(locations)
    distances = matrix["distances"]
    durations = matrix["durations"]
    n = len(locations)

    total_dist = total_dur = 0.0
    for i in range(n - 1):
        total_dist += distances[i][i + 1]
        total_dur += durations[i][i + 1]
    # Return to start.
    total_dist += distances[n - 1][0]
    total_dur += durations[n - 1][0]

    return {
        "distance_km": round(total_dist, 2),
        "duration_min": round(total_dur, 1),
        "stop_count": len(ordered_shipments),
        "affected_stores": affected,
    }


def reoptimize(
    vehicle_id: Optional[str] = None,
    affected_vehicle_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Compute a before/after re-optimization preview (does not persist).

    Raises:
        KeyError: if the vehicle or an approved plan cannot be found.
        ValueError: if there are no remaining stops or the solver is infeasible.
    """
    vehicle_ids = affected_vehicle_ids or ([vehicle_id] if vehicle_id else [])
    if not vehicle_ids:
        raise ValueError("Provide a vehicle_id or affected_vehicle_ids.")
    primary = vehicle_ids[0]

    plan = data_access.load_route_plan()

    # Aggregate unvisited stops across all affected vehicles.
    remaining: List[Dict[str, Any]] = []
    for vid in vehicle_ids:
        remaining.extend(_remaining_shipments_for_vehicle(vid, plan))
    # De-duplicate by shipment_id (urgent orders may repeat across vehicles).
    seen: set = set()
    unique_remaining: List[Dict[str, Any]] = []
    for s in remaining:
        if s["shipment_id"] not in seen:
            seen.add(s["shipment_id"])
            unique_remaining.append(s)

    if not unique_remaining:
        raise ValueError("No unvisited stops remain for the selected vehicle(s).")

    loc = _vehicle_location(primary)
    if loc is None or not loc.get("current_location"):
        raise KeyError(primary)
    start_location = {
        "id": "CURRENT_POS",
        "name": f"{primary} current position",
        "lat": loc["current_location"]["lat"],
        "lon": loc["current_location"]["lon"],
    }

    # "Before" = current plan's remaining stops in their original order.
    before = _route_metrics_for_order(
        {"lat": start_location["lat"], "lon": start_location["lon"]}, unique_remaining
    )

    # "After" = solver re-optimizes those same stops from the current position.
    fleet = [_vehicle_with_driver(vid) for vid in vehicle_ids]
    fleet = [f for f in fleet if f]
    result = reoptimize_remaining_tool(start_location, unique_remaining, fleet)
    if result.get("status") != "ok":
        raise ValueError(result.get("reason", "Re-optimization is infeasible."))

    new_plan = result["plan"]
    new_plan_id = f"REOPT-{datetime.now(_IST).strftime('%Y%m%d-%H%M%S')}-{primary}"
    new_plan["plan_id"] = new_plan_id
    new_plan["reoptimized_for"] = vehicle_ids

    after = {
        "distance_km": new_plan["totals"]["total_distance_km"],
        "duration_min": new_plan["totals"]["total_duration_min"],
        "stop_count": sum(len(r["stops"]) for r in new_plan["routes"]),
        "affected_stores": [
            st["store_name"] for r in new_plan["routes"] for st in r["stops"]
        ],
    }

    with _cache_lock:
        _reopt_cache[new_plan_id] = {
            "plan": new_plan,
            "vehicle_ids": vehicle_ids,
            "before": before,
            "after": after,
        }

    logger.info(
        "Re-optimization preview %s: %.1f->%.1f km", new_plan_id,
        before["distance_km"], after["distance_km"],
    )
    return {"plan_id": new_plan_id, "before": before, "after": after, "plan": new_plan}


def confirm_reoptimize(plan_id: str) -> Dict[str, Any]:
    """Persist a previewed re-optimization and notify materially affected stores.

    Writes the revised plan to ``route_plan_sample.json``, updates shipment
    assignments, and emails each store whose ETA changed by more than the
    configured deviation threshold versus the previously approved plan.
    """
    with _cache_lock:
        cached = _reopt_cache.get(plan_id)
    if cached is None:
        raise KeyError(plan_id)

    new_plan = cached["plan"]
    threshold = _threshold_min()

    # Map old ETAs per store from the currently approved plan.
    old_plan = data_access.load_route_plan()
    old_eta: Dict[str, str] = {}
    for route in old_plan.get("routes", []):
        for stop in route.get("stops", []):
            old_eta[stop["store_id"]] = stop.get("eta", "")

    stores = data_access.get_stores_by_id()
    notified: List[str] = []
    for route in new_plan["routes"]:
        for stop in route["stops"]:
            store_id = stop["store_id"]
            new_e = stop.get("eta", "")
            delta = _eta_delta_min(old_eta.get(store_id), new_e)
            if delta is not None and abs(delta) > threshold:
                store = stores.get(store_id, {})
                send_alert_tool(
                    alert_type="store_notified",
                    severity="info",
                    message=(
                        f"Revised ETA for {store.get('store_name', store_id)}: {new_e} "
                        f"(changed by {delta:+.0f} min after re-optimization)."
                    ),
                    channel=["email", "dashboard"],
                    shipment_id=stop.get("shipment_id"),
                    email_to=store.get("email"),
                    email_subject="Revised delivery ETA",
                )
                notified.append(store.get("store_name", store_id))

    # Persist the revised plan + shipment assignments.
    approved = dict(new_plan)
    approved["status"] = "approved"
    approved["approved_at"] = _now_ist_iso()
    approved["approved_by"] = "Warehouse Dispatch Manager (re-optimized)"
    data_access.save_route_plan(approved)

    assignments: Dict[str, str] = {}
    for route in new_plan["routes"]:
        for stop in route["stops"]:
            assignments[stop["shipment_id"]] = route["vehicle_id"]
    data_access.update_shipment_assignments(plan_id, assignments)

    with _cache_lock:
        _reopt_cache.pop(plan_id, None)

    logger.info("Confirmed re-optimization %s (%d stores notified)", plan_id, len(notified))
    return {
        "status": "approved",
        "plan_id": plan_id,
        "message": "Revised route plan approved and persisted.",
        "notified_stores": notified,
    }


def _eta_delta_min(old_eta: Optional[str], new_eta: Optional[str]) -> Optional[float]:
    """Minutes between two ``"HH:MM"`` ETAs (new - old), or ``None`` if unknown."""
    if not old_eta or not new_eta:
        return None
    try:
        oh, om = old_eta.split(":")
        nh, nm = new_eta.split(":")
        return (int(nh) * 60 + int(nm)) - (int(oh) * 60 + int(om))
    except (ValueError, AttributeError):
        return None
