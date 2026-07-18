"""query_fleet_tool — read-only fleet lookup for the chat assistant.

Filters ``vehicles.json`` (joined with ``drivers.json``) by ``status`` or
``vehicle_id``; optionally merges live ETA-deviation data from
``vehicle_locations.json`` when the question is about delays.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app import data_access
from app.core_logger import get_tool_logger

logger = get_tool_logger("query_fleet")


def query_fleet_tool(filters: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Filter vehicles and return matching records with driver info.

    Args:
        filters: Optional dict with any of:
            - ``vehicle_id``      (str): exact match
            - ``status``          (str): ``available`` | ``maintenance`` | ``en_route`` | …
            - ``include_location`` (bool): if True, merge live location + ETA deviation

    Returns:
        ``{ "count": int, "vehicles": [...] }``
        Each vehicle includes a ``driver`` sub-object and optionally a
        ``location`` sub-object with ``eta_deviation_min``.
    """
    filters = filters or {}
    vehicles = data_access.load_vehicles()
    drivers = data_access.get_drivers_by_id()

    vid = filters.get("vehicle_id")
    status = filters.get("status")
    include_location = filters.get("include_location", False)

    # Load live locations once if needed
    locations: Dict[str, Any] = {}
    if include_location:
        try:
            feed = data_access.load_vehicle_locations()
            for loc in feed.get("vehicles", []):
                locations[loc["vehicle_id"]] = loc
        except Exception:  # noqa: BLE001
            pass

    results: List[Dict[str, Any]] = []
    for v in vehicles:
        if vid and v.get("vehicle_id") != vid:
            continue
        if status and v.get("status") != status:
            continue
        merged = dict(v)
        merged["driver"] = drivers.get(v.get("assigned_driver_id"))
        if include_location and v["vehicle_id"] in locations:
            merged["location"] = locations[v["vehicle_id"]]
        results.append(merged)

    logger.info("query_fleet_tool: filters=%s → %d matches", filters, len(results))
    return {"count": len(results), "vehicles": results}
