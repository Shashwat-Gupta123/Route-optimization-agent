"""ETA-deviation detection tool.

``detect_eta_deviation_tool`` compares a vehicle's *current* position and speed
against its planned route to estimate a revised ETA to the next stop, then
reports how many minutes it deviates from the originally planned ETA.

In demo mode the simulated GPS feed (``vehicle_locations.json``) already carries
an ``eta_deviation_min`` that the simulate endpoints bump directly; this tool
still recomputes a physics-based estimate from the current location/speed so the
logic is real and would keep working against a genuine GPS feed later.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

from app.config import get_config
from app.core_logger import get_tool_logger
from app.agent.tools.common import haversine_km, hhmm_to_minutes, minutes_to_hhmm

logger = get_tool_logger("detect_eta_deviation")

_IST = timezone(timedelta(hours=5, minutes=30))
# Road-network correction over straight-line distance (matches route_matrix).
_ROAD_FACTOR = 1.3
_MIN_SPEED_KMPH = 5.0  # avoid div-by-zero / absurd ETAs when a vehicle crawls


def _now_minutes() -> int:
    now = datetime.now(_IST)
    return now.hour * 60 + now.minute


def detect_eta_deviation_tool(
    vehicle: Dict[str, Any],
    next_stop_location: Optional[Dict[str, float]] = None,
    planned_eta: Optional[str] = None,
    now_min: Optional[int] = None,
) -> Dict[str, Any]:
    """Estimate a vehicle's revised ETA and its deviation from plan.

    Args:
        vehicle: A record from ``vehicle_locations.json`` (needs
            ``current_location``, ``current_speed_kmph`` and, as a fallback,
            ``eta_next_stop`` / ``eta_deviation_min``).
        next_stop_location: ``{"lat", "lon"}`` of the next stop; when omitted the
            tool falls back to the feed's pre-computed ``eta_deviation_min``.
        planned_eta: Originally planned ``"HH:MM"`` ETA to the next stop; defaults
            to the vehicle's ``eta_next_stop``.
        now_min: Current time as minutes-from-midnight (defaults to now, IST).
            Injectable so the pipeline stays deterministic in tests.

    Returns:
        Dict with ``vehicle_id``, ``revised_eta`` (``"HH:MM"``),
        ``eta_deviation_min`` (positive = late), ``threshold_min``, and
        ``exceeds_threshold`` (bool).
    """
    threshold = int(get_config().get("alerting", {}).get("eta_deviation_threshold_min", 10))
    vehicle_id = vehicle.get("vehicle_id")
    planned = planned_eta or vehicle.get("eta_next_stop")
    now_m = now_min if now_min is not None else _now_minutes()

    deviation: float
    revised_eta: Optional[str]

    current = vehicle.get("current_location") or {}
    speed = float(vehicle.get("current_speed_kmph") or 0.0)

    if next_stop_location and current.get("lat") is not None and planned:
        # Physics-based estimate: travel time from here to the next stop.
        dist_km = haversine_km(
            (current["lat"], current["lon"]),
            (next_stop_location["lat"], next_stop_location["lon"]),
        ) * _ROAD_FACTOR
        eff_speed = max(speed, _MIN_SPEED_KMPH)
        travel_min = dist_km / eff_speed * 60.0
        revised_min = now_m + travel_min
        planned_min = hhmm_to_minutes(planned)
        deviation = revised_min - planned_min
        revised_eta = minutes_to_hhmm(revised_min)
    else:
        # Fallback: trust the simulated feed's pre-computed deviation.
        deviation = float(vehicle.get("eta_deviation_min") or 0.0)
        revised_eta = planned

    deviation = round(deviation, 1)
    exceeds = deviation > threshold
    logger.info(
        "ETA deviation for %s: %.1f min (threshold %d, exceeds=%s)",
        vehicle_id, deviation, threshold, exceeds,
    )
    return {
        "vehicle_id": vehicle_id,
        "revised_eta": revised_eta,
        "eta_deviation_min": deviation,
        "threshold_min": threshold,
        "exceeds_threshold": exceeds,
    }
