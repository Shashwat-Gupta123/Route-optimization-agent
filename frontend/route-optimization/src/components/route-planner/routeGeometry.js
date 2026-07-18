/**
 * Fetch actual road-following geometries for route legs using the free OSRM
 * public demo API (no API key required).
 *
 * Each call returns an array of [lat, lng] pairs tracing the real road path
 * between two coordinates. Results are cached in-memory so identical legs
 * aren't re-fetched.
 *
 * Falls back to a simple straight line (the two endpoints) if OSRM is
 * unavailable or rate-limited.
 */

const OSRM_BASE = "https://router.project-osrm.org/route/v1/driving";

/** In-memory geometry cache: "lat1,lon1|lat2,lon2" → [[lat, lng], …] */
const _cache = new Map();

/**
 * Build a deterministic cache key for a leg.
 * Rounds to 5 decimals to avoid floating-point duplicates.
 */
function _cacheKey(fromLat, fromLon, toLat, toLon) {
    const r = (v) => Number(v).toFixed(5);
    return `${r(fromLat)},${r(fromLon)}|${r(toLat)},${r(toLon)}`;
}

/**
 * Fetch the road geometry for a single leg from OSRM.
 * @returns {Promise<[number, number][]>} Array of [lat, lng] pairs
 */
async function _fetchLegGeometry(fromLat, fromLon, toLat, toLon) {
    const key = _cacheKey(fromLat, fromLon, toLat, toLon);
    if (_cache.has(key)) return _cache.get(key);

    const fallback = [
        [fromLat, fromLon],
        [toLat, toLon],
    ];

    try {
        // OSRM expects lon,lat order
        const url =
            `${OSRM_BASE}/${fromLon},${fromLat};${toLon},${toLat}` +
            `?overview=full&geometries=geojson`;

        const resp = await fetch(url);
        if (!resp.ok) throw new Error(`OSRM ${resp.status}`);

        const data = await resp.json();
        const coords = data?.routes?.[0]?.geometry?.coordinates;

        if (!coords || coords.length === 0) {
            _cache.set(key, fallback);
            return fallback;
        }

        // GeoJSON coordinates are [lon, lat] — flip to [lat, lng] for Leaflet
        const latLngs = coords.map(([lon, lat]) => [lat, lon]);
        _cache.set(key, latLngs);
        return latLngs;
    } catch {
        // Network error or rate limit — fall back to straight line
        _cache.set(key, fallback);
        return fallback;
    }
}

/**
 * Fetch road geometries for all legs across all visible plans.
 *
 * @param {Array} plans - The plan objects (each with routes[].legs[])
 * @param {Set} visiblePlanIds - Which plans are currently toggled on
 * @returns {Promise<Map<string, [number, number][]>>}
 *   Map keyed by "planId-vehicleId-legIdx" → array of [lat, lng] road coords
 */
export async function fetchAllLegGeometries(plans, visiblePlanIds) {
    /** @type {Map<string, [number, number][]>} */
    const result = new Map();
    const tasks = [];

    for (const plan of plans) {
        if (!visiblePlanIds.has(plan.plan_id)) continue;

        for (const route of plan.routes) {
            for (let idx = 0; idx < (route.legs || []).length; idx++) {
                const leg = route.legs[idx];
                const mapKey = `${plan.plan_id}-${route.vehicle_id}-${idx}`;

                tasks.push(
                    _fetchLegGeometry(
                        leg.from_lat,
                        leg.from_lon,
                        leg.to_lat,
                        leg.to_lon,
                    ).then((geom) => {
                        result.set(mapKey, geom);
                    }),
                );
            }
        }
    }

    // Fire all fetches concurrently (cache hits resolve synchronously)
    await Promise.all(tasks);
    return result;
}

/**
 * Clear the geometry cache (useful when plans are regenerated).
 */
export function clearGeometryCache() {
    _cache.clear();
}
