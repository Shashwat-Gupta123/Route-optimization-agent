"""Route matrix + geocoding tool.

Wraps two free OpenStreetMap-based services:

* **OpenRouteService (ORS) Matrix API** — distance/duration between the
  warehouse and every store. The API key is read from the env var whose name is
  stored in ``config.json`` (``api_config.routing_api_key_env_var``).
* **Nominatim** — forward geocoding for any store that is missing ``lat``/``lon``.

Both calls degrade gracefully: if ORS is unavailable or rate-limited, a
haversine distance matrix (with an average-speed duration estimate) is returned
so the planner still works offline. Coordinates are always ordered ``[lon, lat]``
for ORS, distances are km and durations are minutes in the returned matrix.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import requests

from app.config import get_config, get_env
from app.core_logger import get_tool_logger
from app.agent.tools.common import haversine_km

logger = get_tool_logger("route_matrix")

ORS_MATRIX_URL = "https://api.openrouteservice.org/v2/matrix/driving-hgv"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
# Average fleet speed (km/h) used for the offline duration fallback.
_FALLBACK_SPEED_KMPH = 32.0
_HTTP_TIMEOUT = 12  # seconds


def _geocode_address(address: str) -> Optional[Tuple[float, float]]:
    """Forward-geocode a free-text address to ``(lat, lon)`` via Nominatim."""
    cfg = get_config()
    user_agent = cfg["api_config"].get("geocoding_user_agent", "route-planner/1.0")
    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={"q": address, "format": "json", "limit": 1},
            headers={"User-Agent": user_agent},
            timeout=_HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.warning("Nominatim geocoding failed for %r: %s", address, exc)
    return None


def _fallback_matrix(coords: List[Tuple[float, float]]) -> Dict[str, List[List[float]]]:
    """Build a haversine distance/duration matrix when ORS is unavailable."""
    n = len(coords)
    distances = [[0.0] * n for _ in range(n)]
    durations = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            km = haversine_km(coords[i], coords[j])
            # Small road-network correction factor over straight-line distance.
            km *= 1.3
            distances[i][j] = round(km, 3)
            durations[i][j] = round(km / _FALLBACK_SPEED_KMPH * 60.0, 2)
    return {"distances": distances, "durations": durations}


def get_route_matrix_tool(
    locations: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Return a distance (km) and duration (min) matrix between locations.

    Args:
        locations: Ordered list of points, index 0 being the warehouse. Each
            item is a dict with ``lat``/``lon`` (preferred) and optionally an
            ``address`` used as a geocoding fallback when coordinates are absent.

    Returns:
        Dict with ``distances`` and ``durations`` (both N x N matrices),
        ``coords`` (the resolved ``(lat, lon)`` list) and ``source`` indicating
        whether ``openrouteservice`` or the ``haversine`` fallback was used.
    """
    coords: List[Tuple[float, float]] = []
    for loc in locations:
        lat, lon = loc.get("lat"), loc.get("lon")
        if lat is None or lon is None:
            geocoded = _geocode_address(loc.get("address", ""))
            if geocoded is None:
                raise ValueError(
                    f"Missing coordinates for location {loc.get('store_id') or loc.get('name')}"
                )
            lat, lon = geocoded
        coords.append((float(lat), float(lon)))

    cfg = get_config()
    api_key_env = cfg["api_config"].get("routing_api_key_env_var")
    api_key = get_env(api_key_env) if api_key_env else None

    if api_key:
        try:
            body = {
                # ORS expects [lon, lat]
                "locations": [[lon, lat] for (lat, lon) in coords],
                "metrics": ["distance", "duration"],
                "units": "km",
            }
            resp = requests.post(
                ORS_MATRIX_URL,
                json=body,
                headers={
                    "Authorization": api_key,
                    "Content-Type": "application/json",
                },
                timeout=_HTTP_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            distances = data["distances"]
            # ORS durations are seconds -> convert to minutes.
            durations = [[(v or 0) / 60.0 for v in row] for row in data["durations"]]
            logger.info("Route matrix built via OpenRouteService (%d points)", len(coords))
            return {
                "distances": distances,
                "durations": durations,
                "coords": [list(c) for c in coords],
                "source": "openrouteservice",
            }
        except (requests.RequestException, KeyError, ValueError) as exc:
            logger.warning("ORS matrix failed, using haversine fallback: %s", exc)

    matrix = _fallback_matrix(coords)
    matrix["coords"] = [list(c) for c in coords]
    matrix["source"] = "haversine"
    logger.info("Route matrix built via haversine fallback (%d points)", len(coords))
    return matrix
