"""OR-Tools VRP solver tool.

``optimize_routes_tool`` is a pure function: it takes plain dicts (shipments,
fleet, and a distance/duration matrix) and returns three alternative route plans
— ``fastest``, ``cheapest`` and ``balanced`` — as plain dicts. No OR-Tools
objects cross the function boundary.

Modelling summary
-----------------
* Node 0 is the warehouse (depot); nodes 1..N are shipments (one per store).
* A **capacity** dimension enforces each vehicle's ``capacity_kg``.
* A **time** dimension accumulates travel + per-stop service time and enforces
  each shipment's ``[earliest, latest]`` delivery window (minutes from midnight).
* The three plans differ only in the arc-cost objective:
    - ``fastest``  -> minimise travel duration
    - ``cheapest`` -> minimise travel distance
    - ``balanced`` -> minimise a normalised blend of duration and distance
* Post-solve, per-vehicle fuel cost, CO2 and capacity utilisation are derived
  from ``config.json`` factors, and a comparative ``effectiveness_score`` is
  computed across the three plans using the configured weights.

If any objective yields no feasible assignment, the returned dict has
``status='infeasible'`` with a human-readable ``reason``.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from app.config import get_config
from app.core_logger import get_tool_logger
from app.agent.tools.common import minutes_to_hhmm, hhmm_to_minutes

logger = get_tool_logger("optimize_routes")

_IST = timezone(timedelta(hours=5, minutes=30))
_PLAN_TYPES = ("fastest", "cheapest", "balanced")
_SOLVE_TIME_LIMIT_S = 3


def _now_ist_iso() -> str:
    return datetime.now(_IST).replace(microsecond=0).isoformat()


def _build_index_data(
    warehouse: Dict[str, Any],
    shipments: List[Dict[str, Any]],
    matrix: Dict[str, Any],
    horizon_start_min: int,
    horizon_end_min: int,
    service_min: int,
) -> Dict[str, Any]:
    """Assemble the integer arrays OR-Tools needs (distances in metres,
    durations/time windows in seconds)."""
    distances = matrix["distances"]
    durations = matrix["durations"]

    demands = [0] + [int(round(s["weight_kg"])) for s in shipments]
    dist_m = [[int(round(d * 1000)) for d in row] for row in distances]
    dur_s = [[int(round(d * 60)) for d in row] for row in durations]

    # Time windows in seconds from midnight.
    windows: List[Tuple[int, int]] = [(horizon_start_min * 60, horizon_end_min * 60)]
    for s in shipments:
        earliest = hhmm_to_minutes(s["earliest_delivery_time"])
        latest = hhmm_to_minutes(s["latest_delivery_time"])
        windows.append((earliest * 60, latest * 60))

    return {
        "demands": demands,
        "dist_m": dist_m,
        "dur_s": dur_s,
        "windows": windows,
        "service_s": service_min * 60,
        "horizon_end_s": horizon_end_min * 60,
        "depart_s": horizon_start_min * 60,
    }


def _solve_single(
    data: Dict[str, Any],
    vehicle_caps: List[int],
    plan_type: str,
    weights: Dict[str, float],
) -> Optional[List[List[Tuple[int, int]]]]:
    """Solve the VRP for one objective.

    Returns a list per vehicle of ``(node_index, arrival_time_seconds)`` tuples
    (excluding the depot), or ``None`` if no feasible solution exists.
    """
    n = len(data["demands"])
    num_vehicles = len(vehicle_caps)
    manager = pywrapcp.RoutingIndexManager(n, num_vehicles, 0)
    routing = pywrapcp.RoutingModel(manager)

    dist_m = data["dist_m"]
    dur_s = data["dur_s"]
    service_s = data["service_s"]

    def duration_cost(from_index: int, to_index: int) -> int:
        i = manager.IndexToNode(from_index)
        j = manager.IndexToNode(to_index)
        return dur_s[i][j]

    def distance_cost(from_index: int, to_index: int) -> int:
        i = manager.IndexToNode(from_index)
        j = manager.IndexToNode(to_index)
        return dist_m[i][j]

    def balanced_cost(from_index: int, to_index: int) -> int:
        i = manager.IndexToNode(from_index)
        j = manager.IndexToNode(to_index)
        # Convert distance (m) to a time-equivalent (~32 km/h) so the two terms
        # are comparable, then blend using the configured time/distance weights.
        dist_time_equiv = dist_m[i][j] / 8.9
        w_time = weights.get("time", 0.3)
        w_dist = weights.get("distance", 0.3)
        denom = (w_time + w_dist) or 1.0
        return int((w_time * dur_s[i][j] + w_dist * dist_time_equiv) / denom)

    cost_fn = {
        "fastest": duration_cost,
        "cheapest": distance_cost,
        "balanced": balanced_cost,
    }[plan_type]
    cost_index = routing.RegisterTransitCallback(cost_fn)
    routing.SetArcCostEvaluatorOfAllVehicles(cost_index)

    # Capacity dimension.
    demands = data["demands"]

    def demand_cb(from_index: int) -> int:
        return demands[manager.IndexToNode(from_index)]

    demand_index = routing.RegisterUnaryTransitCallback(demand_cb)
    routing.AddDimensionWithVehicleCapacity(
        demand_index, 0, vehicle_caps, True, "Capacity"
    )

    # Time dimension (travel + service time at the origin node).
    def time_cb(from_index: int, to_index: int) -> int:
        i = manager.IndexToNode(from_index)
        j = manager.IndexToNode(to_index)
        svc = 0 if i == 0 else service_s
        return dur_s[i][j] + svc

    time_index = routing.RegisterTransitCallback(time_cb)
    horizon_end_s = data["horizon_end_s"]
    routing.AddDimension(
        time_index,
        4 * 3600,  # allow up to 4h waiting (slack)
        horizon_end_s,
        False,
        "Time",
    )
    time_dim = routing.GetDimensionOrDie("Time")

    windows = data["windows"]
    for node in range(1, n):
        index = manager.NodeToIndex(node)
        time_dim.CumulVar(index).SetRange(windows[node][0], windows[node][1])

    depart_s = data["depart_s"]
    for v in range(num_vehicles):
        start = routing.Start(v)
        time_dim.CumulVar(start).SetRange(depart_s, horizon_end_s)

    search_params = pywrapcp.DefaultRoutingSearchParameters()
    search_params.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_params.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_params.time_limit.FromSeconds(_SOLVE_TIME_LIMIT_S)

    solution = routing.SolveWithParameters(search_params)
    if solution is None:
        return None

    routes: List[List[Tuple[int, int]]] = []
    for v in range(num_vehicles):
        index = routing.Start(v)
        route: List[Tuple[int, int]] = []
        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            arrival = solution.Value(time_dim.CumulVar(index))
            if node != 0:
                route.append((node, arrival))
            index = solution.Value(routing.NextVar(index))
        routes.append(route)
    return routes


def _assemble_plan(
    plan_type: str,
    solution: List[List[Tuple[int, int]]],
    warehouse: Dict[str, Any],
    shipments: List[Dict[str, Any]],
    stores_by_id: Dict[str, Dict[str, Any]],
    vehicles: List[Dict[str, Any]],
    matrix: Dict[str, Any],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """Turn a solver solution into a RoutePlan-shaped dict with legs/ETAs/costs."""
    coords = matrix["coords"]  # index-aligned [lat, lon]; index 0 = warehouse
    distances = matrix["distances"]
    durations = matrix["durations"]
    fuel_price = config["default_fuel_price_inr_per_l"]
    co2_factors = config["co2_emission_factor_kg_per_km"]

    wh_id = warehouse["warehouse_id"]
    wh_name = warehouse.get("name", "Warehouse")
    wh_lat, wh_lon = warehouse["lat"], warehouse["lon"]

    routes_out: List[Dict[str, Any]] = []
    total_distance = total_duration = total_fuel = total_co2 = 0.0
    makespan = 0.0

    for v_idx, route in enumerate(solution):
        if not route:
            continue
        vehicle = vehicles[v_idx]
        cap = vehicle["capacity_kg"]
        efficiency = vehicle["fuel_efficiency_km_per_l"]
        vtype = vehicle["type"]
        co2_factor = co2_factors.get(vtype, 0.3)

        stops: List[Dict[str, Any]] = []
        legs: List[Dict[str, Any]] = []
        route_distance = 0.0
        route_duration = 0.0
        load_used = sum(shipments[node - 1]["weight_kg"] for node, _ in route)
        load_remaining = load_used
        last_arrival = route[-1][1]

        prev_node = 0
        prev_name = wh_name
        prev_lat, prev_lon = wh_lat, wh_lon
        for node, arrival_s in route:
            shipment = shipments[node - 1]
            store = stores_by_id.get(shipment["store_id"], {})
            lat, lon = coords[node]
            eta = minutes_to_hhmm(arrival_s / 60.0)

            leg_dist = distances[prev_node][node]
            leg_dur = durations[prev_node][node]
            route_distance += leg_dist
            route_duration += leg_dur
            legs.append(
                {
                    "from_stop": wh_id if prev_node == 0 else shipments[prev_node - 1]["store_id"],
                    "to_stop": shipment["store_id"],
                    "from_name": prev_name,
                    "to_name": store.get("store_name", shipment["store_id"]),
                    "from_lat": prev_lat,
                    "from_lon": prev_lon,
                    "to_lat": lat,
                    "to_lon": lon,
                    "distance_km": round(leg_dist, 2),
                    "duration_min": round(leg_dur, 1),
                    "eta": eta,
                }
            )
            stops.append(
                {
                    "store_id": shipment["store_id"],
                    "shipment_id": shipment["shipment_id"],
                    "store_name": store.get("store_name", shipment["store_id"]),
                    "eta": eta,
                    "lat": lat,
                    "lon": lon,
                    "load_after_stop_kg": round(max(0.0, load_remaining - shipment["weight_kg"]), 1),
                }
            )
            load_remaining -= shipment["weight_kg"]
            prev_node = node
            prev_name = store.get("store_name", shipment["store_id"])
            prev_lat, prev_lon = lat, lon

        # Return leg to the warehouse.
        return_dist = distances[prev_node][0]
        return_dur = durations[prev_node][0]
        route_distance += return_dist
        route_duration += return_dur
        legs.append(
            {
                "from_stop": shipments[prev_node - 1]["store_id"],
                "to_stop": wh_id,
                "from_name": prev_name,
                "to_name": wh_name,
                "from_lat": prev_lat,
                "from_lon": prev_lon,
                "to_lat": wh_lat,
                "to_lon": wh_lon,
                "distance_km": round(return_dist, 2),
                "duration_min": round(return_dur, 1),
                "eta": minutes_to_hhmm((last_arrival + return_dur * 60) / 60.0),
            }
        )

        fuel_cost = (route_distance / efficiency) * fuel_price if efficiency else 0.0
        co2 = route_distance * co2_factor
        capacity_pct = (load_used / cap * 100.0) if cap else 0.0
        makespan = max(makespan, (last_arrival - route[0][1]) / 60.0, route_duration)

        driver = vehicle.get("driver") or {}
        routes_out.append(
            {
                "vehicle_id": vehicle["vehicle_id"],
                "driver_id": vehicle.get("assigned_driver_id"),
                "driver_name": driver.get("name"),
                "vehicle_type": vtype,
                "stops": stops,
                "legs": legs,
                "distance_km": round(route_distance, 2),
                "duration_min": round(route_duration, 1),
                "fuel_cost_inr": round(fuel_cost, 2),
                "co2_emissions_kg": round(co2, 2),
                "capacity_used_pct": round(capacity_pct, 1),
            }
        )
        total_distance += route_distance
        total_duration += route_duration
        total_fuel += fuel_cost
        total_co2 += co2

    plan = {
        "plan_id": "",  # filled by caller
        "plan_name": plan_type,
        "warehouse_id": wh_id,
        "generated_at": _now_ist_iso(),
        "routes": routes_out,
        "totals": {
            "total_distance_km": round(total_distance, 2),
            "total_duration_min": round(total_duration, 1),
            "total_fuel_cost_inr": round(total_fuel, 2),
            "total_co2_emissions_kg": round(total_co2, 2),
            "makespan_min": round(makespan, 1),
            "on_time_pct": 100.0,
        },
        "effectiveness_score": 0.0,  # filled comparatively below
        "status": "draft",
    }
    return plan


def _score_plans(plans: List[Dict[str, Any]], weights: Dict[str, float]) -> None:
    """Assign a comparative 0-10 effectiveness score to each plan in place.

    For every metric (all lower-is-better) the best plan scores 1.0 and the
    worst 0.0; the weighted blend is scaled to 0-10.
    """
    metrics = {
        "distance": [p["totals"]["total_distance_km"] for p in plans],
        "time": [p["totals"]["total_duration_min"] for p in plans],
        "fuel_cost": [p["totals"]["total_fuel_cost_inr"] for p in plans],
        "emissions": [p["totals"]["total_co2_emissions_kg"] for p in plans],
    }
    norms: Dict[str, List[float]] = {}
    for key, values in metrics.items():
        lo, hi = min(values), max(values)
        span = hi - lo
        norms[key] = [1.0 if span == 0 else (hi - v) / span for v in values]

    for i, plan in enumerate(plans):
        score = (
            weights.get("distance", 0.3) * norms["distance"][i]
            + weights.get("time", 0.3) * norms["time"][i]
            + weights.get("fuel_cost", 0.25) * norms["fuel_cost"][i]
            + weights.get("emissions", 0.15) * norms["emissions"][i]
        )
        plan["effectiveness_score"] = round(score * 10.0, 1)


def optimize_routes_tool(
    warehouse: Dict[str, Any],
    shipments: List[Dict[str, Any]],
    fleet: List[Dict[str, Any]],
    matrix: Dict[str, Any],
) -> Dict[str, Any]:
    """Generate fastest/cheapest/balanced route plans for today's shipments.

    Args:
        warehouse: The depot record (needs ``warehouse_id``, ``lat``, ``lon``).
        shipments: Today's shipments; each needs ``shipment_id``, ``store_id``,
            ``weight_kg`` and delivery-window times. Order must match the matrix
            (shipment ``k`` maps to matrix node ``k + 1``).
        fleet: Available vehicles (with capacity, fuel efficiency, type, driver).
        matrix: Output of :func:`get_route_matrix_tool` (``distances``/
            ``durations``/``coords`` with the warehouse at index 0).

    Returns:
        ``{"plans": [ ...3 RoutePlan dicts... ]}`` on success, or
        ``{"status": "infeasible", "reason": <str>}`` if no assignment satisfies
        the capacity and time-window constraints.
    """
    config = get_config()
    weights = config["effectiveness_score_weights"]
    service_min = int(config.get("default_avg_service_time_min", 8))
    horizon = config["planning_horizon"]
    horizon_start = hhmm_to_minutes(horizon["start_time"])
    horizon_end = hhmm_to_minutes(horizon["end_time"])

    stores_by_id = {s["store_id"]: s for s in _stores_from_shipments(shipments)}
    vehicle_caps = [int(round(v["capacity_kg"])) for v in fleet]

    total_demand = sum(s["weight_kg"] for s in shipments)
    total_capacity = sum(v["capacity_kg"] for v in fleet)
    if total_demand > total_capacity:
        return {
            "status": "infeasible",
            "reason": (
                f"Total shipment weight ({total_demand:.0f} kg) exceeds available "
                f"fleet capacity ({total_capacity:.0f} kg). Add vehicles or reduce load."
            ),
        }

    data = _build_index_data(
        warehouse, shipments, matrix, horizon_start, horizon_end, service_min
    )

    plans: List[Dict[str, Any]] = []
    for plan_type in _PLAN_TYPES:
        solution = _solve_single(data, vehicle_caps, plan_type, weights)
        if solution is None:
            return {
                "status": "infeasible",
                "reason": (
                    "No feasible route found for objective "
                    f"'{plan_type}'. Likely causes: delivery time windows too "
                    "tight, or a single shipment exceeds every vehicle's capacity."
                ),
            }
        plan = _assemble_plan(
            plan_type, solution, warehouse, shipments,
            stores_by_id, fleet, matrix, config,
        )
        plans.append(plan)

    _score_plans(plans, weights)
    logger.info(
        "Generated %d plans (source=%s)", len(plans), matrix.get("source")
    )
    return {"plans": plans}


def _stores_from_shipments(shipments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract embedded store records carried on shipments (``shipment['store']``)."""
    stores: List[Dict[str, Any]] = []
    for s in shipments:
        store = s.get("store")
        if store:
            stores.append(store)
    return stores
