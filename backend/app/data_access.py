"""Data access layer.

Single point of truth for reading and writing the flat JSON files under
``backend/db/``. Every path is resolved through :mod:`app.config` (which reads
``config.json``'s ``data_files`` section) so filenames are never hardcoded here.

Keeping all disk I/O behind this module means a future migration to
SQLite/Postgres only needs to change this file, not the rest of the app.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import resolve_data_file

# Guards concurrent writes to the JSON files (FastAPI runs handlers in threads).
_write_lock = threading.Lock()

_IST = timezone(timedelta(hours=5, minutes=30))


def _now_ist_iso() -> str:
    return datetime.now(_IST).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _write_json(path: Path, data: Any) -> None:
    """Atomically write ``data`` as pretty JSON to ``path``."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    tmp.replace(path)


# --- Readers -----------------------------------------------------------------

def load_warehouse() -> Dict[str, Any]:
    return _read_json(resolve_data_file("warehouse"))


def load_vehicles() -> List[Dict[str, Any]]:
    return _read_json(resolve_data_file("vehicles"))


def load_drivers() -> List[Dict[str, Any]]:
    return _read_json(resolve_data_file("drivers"))


def load_stores() -> List[Dict[str, Any]]:
    return _read_json(resolve_data_file("stores"))


def load_shipments() -> List[Dict[str, Any]]:
    return _read_json(resolve_data_file("shipments"))


def load_route_plan() -> Dict[str, Any]:
    return _read_json(resolve_data_file("route_plans"))


def load_vehicle_locations() -> Dict[str, Any]:
    """Return the simulated live-GPS feed (``vehicle_locations.json``).

    Treated exactly like a live tracking API response — callers must re-read it
    rather than caching, since the demo simulation endpoints mutate it.
    """
    return _read_json(resolve_data_file("vehicle_locations"))


def load_alerts() -> List[Dict[str, Any]]:
    return _read_json(resolve_data_file("alerts"))


def load_route_history() -> List[Dict[str, Any]]:
    """Return the historical planned-vs-actual daily route performance records."""
    return _read_json(resolve_data_file("route_history"))


# --- Convenience joins -------------------------------------------------------

def get_stores_by_id() -> Dict[str, Dict[str, Any]]:
    return {s["store_id"]: s for s in load_stores()}


def get_drivers_by_id() -> Dict[str, Dict[str, Any]]:
    return {d["driver_id"]: d for d in load_drivers()}


def get_vehicles_by_id() -> Dict[str, Dict[str, Any]]:
    return {v["vehicle_id"]: v for v in load_vehicles()}


def get_available_fleet() -> List[Dict[str, Any]]:
    """Return available vehicles joined with their assigned driver record."""
    drivers = get_drivers_by_id()
    fleet: List[Dict[str, Any]] = []
    for vehicle in load_vehicles():
        if vehicle.get("status") != "available":
            continue
        merged = dict(vehicle)
        merged["driver"] = drivers.get(vehicle.get("assigned_driver_id"))
        fleet.append(merged)
    return fleet


def get_shipments_with_store() -> List[Dict[str, Any]]:
    """Return today's shipments joined with their store's delivery details."""
    stores = get_stores_by_id()
    result: List[Dict[str, Any]] = []
    for shipment in load_shipments():
        merged = dict(shipment)
        merged["store"] = stores.get(shipment.get("store_id"))
        result.append(merged)
    return result


# --- Writers -----------------------------------------------------------------

def save_route_plan(plan: Dict[str, Any]) -> None:
    """Persist the approved plan to ``route_plan_sample.json``."""
    with _write_lock:
        _write_json(resolve_data_file("route_plans"), plan)


def update_shipment_assignments(
    plan_id: str, assignments: Dict[str, str]
) -> List[Dict[str, Any]]:
    """Mark shipments as assigned once a plan is approved.

    ``assignments`` maps ``shipment_id`` -> ``vehicle_id``. Matching shipments
    get ``status='assigned'`` plus ``assigned_plan_id`` / ``assigned_vehicle_id``.
    """
    with _write_lock:
        path = resolve_data_file("shipments")
        shipments = _read_json(path)
        for shipment in shipments:
            sid = shipment.get("shipment_id")
            if sid in assignments:
                shipment["status"] = "assigned"
                shipment["assigned_plan_id"] = plan_id
                shipment["assigned_vehicle_id"] = assignments[sid]
        _write_json(path, shipments)
        return shipments


# --- Component 2 writers (real-time monitoring) ------------------------------

def save_vehicle_locations(data: Dict[str, Any]) -> None:
    """Overwrite the simulated GPS feed with ``data`` (used by demo controls)."""
    with _write_lock:
        _write_json(resolve_data_file("vehicle_locations"), data)


def update_vehicle_location(
    vehicle_id: str, updates: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Apply ``updates`` to one vehicle inside ``vehicle_locations.json``.

    Returns the updated vehicle record, or ``None`` if the id is unknown. Also
    refreshes the feed's ``last_updated`` timestamp so pollers see it changed.
    """
    with _write_lock:
        path = resolve_data_file("vehicle_locations")
        feed = _read_json(path)
        updated: Optional[Dict[str, Any]] = None
        for vehicle in feed.get("vehicles", []):
            if vehicle.get("vehicle_id") == vehicle_id:
                vehicle.update(updates)
                updated = vehicle
                break
        if updated is not None:
            feed["last_updated"] = _now_ist_iso()
            _write_json(path, feed)
        return updated


def append_alert(alert: Dict[str, Any]) -> Dict[str, Any]:
    """Append an alert to ``alerts.json`` and return it."""
    with _write_lock:
        path = resolve_data_file("alerts")
        alerts = _read_json(path)
        alerts.append(alert)
        _write_json(path, alerts)
        return alert


def next_alert_id() -> str:
    """Generate the next ``ALRT####`` id based on the existing alerts."""
    max_num = 2000
    for alert in load_alerts():
        aid = str(alert.get("alert_id", ""))
        digits = "".join(ch for ch in aid if ch.isdigit())
        if digits:
            max_num = max(max_num, int(digits))
    return f"ALRT{max_num + 1}"


def acknowledge_alert(alert_id: str) -> Optional[Dict[str, Any]]:
    """Mark an alert acknowledged; returns the alert or ``None`` if not found."""
    with _write_lock:
        path = resolve_data_file("alerts")
        alerts = _read_json(path)
        target: Optional[Dict[str, Any]] = None
        for alert in alerts:
            if alert.get("alert_id") == alert_id:
                alert["acknowledged"] = True
                target = alert
                break
        if target is not None:
            _write_json(path, alerts)
        return target


def reset_shipments() -> List[Dict[str, Any]]:
    """Reset all shipments to ``pending`` status, clearing any assignment data.

    Useful for demo / testing: lets you re-run route planning after approving
    a plan without having to manually edit ``shipments.json``.
    """
    with _write_lock:
        path = resolve_data_file("shipments")
        shipments = _read_json(path)
        for shipment in shipments:
            shipment["status"] = "pending"
            shipment.pop("assigned_plan_id", None)
            shipment.pop("assigned_vehicle_id", None)
        _write_json(path, shipments)
        return shipments


def add_shipment(shipment: Dict[str, Any]) -> Dict[str, Any]:
    """Append a new (urgent) shipment to ``shipments.json`` and return it."""
    with _write_lock:
        path = resolve_data_file("shipments")
        shipments = _read_json(path)
        shipments.append(shipment)
        _write_json(path, shipments)
        return shipment


def flag_shipments_for_reassignment(vehicle_id: str) -> List[str]:
    """Mark a broken-down vehicle's assigned shipments as needing reassignment.

    Returns the list of affected ``shipment_id``s.
    """
    with _write_lock:
        path = resolve_data_file("shipments")
        shipments = _read_json(path)
        affected: List[str] = []
        for shipment in shipments:
            if shipment.get("assigned_vehicle_id") == vehicle_id and shipment.get(
                "status"
            ) not in ("delivered", "cancelled"):
                shipment["status"] = "needs_reassignment"
                affected.append(shipment["shipment_id"])
        if affected:
            _write_json(path, shipments)
        return affected


# --- Component 5 — Chat session storage --------------------------------------

def _chat_sessions_path() -> Path:
    return resolve_data_file("chat_sessions")


def load_chat_sessions() -> Dict[str, Any]:
    """Return the full sessions dict, creating the file if it doesn't exist."""
    path = _chat_sessions_path()
    if not path.exists():
        _write_json(path, {"sessions": {}})
    data = _read_json(path)
    if "sessions" not in data:
        data["sessions"] = {}
    return data


def get_session(conversation_id: str) -> Dict[str, Any]:
    """Return the session for *conversation_id*, or a fresh blank session."""
    data = load_chat_sessions()
    return data["sessions"].get(conversation_id, {
        "started_at": _now_ist_iso(),
        "last_active_at": _now_ist_iso(),
        "page_context": None,
        "turns": [],
    })


def save_session(conversation_id: str, session: Dict[str, Any]) -> None:
    """Persist *session* under its *conversation_id*; never touches other sessions."""
    with _write_lock:
        path = _chat_sessions_path()
        data = _read_json(path) if path.exists() else {"sessions": {}}
        if "sessions" not in data:
            data["sessions"] = {}
        session["last_active_at"] = _now_ist_iso()
        data["sessions"][conversation_id] = session
        _write_json(path, data)
