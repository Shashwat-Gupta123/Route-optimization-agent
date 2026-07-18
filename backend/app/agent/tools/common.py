"""Small shared helpers used by the route-planning tools and solver."""

from __future__ import annotations

import math
from typing import Tuple


def haversine_km(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    """Great-circle distance in km between two ``(lat, lon)`` points."""
    lat1, lon1 = a
    lat2, lon2 = b
    r = 6371.0  # Earth radius (km)
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(h)))


def minutes_to_hhmm(minutes: float) -> str:
    """Convert minutes-from-midnight to a ``"HH:MM"`` clock string."""
    total = int(round(minutes))
    total %= 24 * 60
    return f"{total // 60:02d}:{total % 60:02d}"


def hhmm_to_minutes(value: str) -> int:
    """Convert a ``"HH:MM"`` clock string to minutes-from-midnight."""
    hours, mins = value.split(":")
    return int(hours) * 60 + int(mins)
