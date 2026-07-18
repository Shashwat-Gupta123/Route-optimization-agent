import { useEffect, useMemo, useRef, useState } from "react";
import {
    MapContainer,
    TileLayer,
    Marker,
    Polyline,
    Tooltip,
    Popup,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { coloredDot, warehouseIcon, shopIcon } from "../mapUtils";
import {
    fetchAllLegGeometries,
    clearGeometryCache,
} from "./routeGeometry";

const PLAN_COLORS = {
    fastest: "var(--route-fastest)",
    cheapest: "var(--route-cheapest)",
    balanced: "var(--route-balanced)",
};
// react-leaflet needs concrete colors, not CSS vars, for SVG strokes.
const PLAN_HEX = {
    fastest: "#2563eb",
    cheapest: "#0d9488",
    balanced: "#d97706",
};

export function planColor(name) {
    return PLAN_HEX[name] || "#2563eb";
}
export { PLAN_COLORS };

/**
 * Interactive Leaflet map for the Route Planner. Renders the warehouse + store
 * markers, and each visible plan's route as individual per-leg polylines so
 * every segment carries its own hover tooltip (from/to, distance, duration, ETA).
 * The selected plan's polylines are drawn thicker; the rest are dimmed.
 *
 * Route polylines follow actual roads via the OSRM routing API.  While the
 * geometries are loading (or if OSRM is unavailable), a straight-line
 * fallback is shown.
 */
export default function RouteMap({
    warehouse,
    shipments,
    plans,
    visiblePlanIds,
    selectedPlanId,
}) {
    const center = warehouse ? [warehouse.lat, warehouse.lon] : [28.5, 77.4];

    // ---- Road-geometry state ------------------------------------------------
    /** @type {[Map<string, [number,number][]>, Function]} */
    const [geometries, setGeometries] = useState(new Map());
    const fetchIdRef = useRef(0); // guard against stale responses

    // Clear the OSRM cache whenever brand-new plans are generated.
    const planFingerprint = plans.map((p) => p.plan_id).join("|");
    const prevFingerprint = useRef(planFingerprint);
    useEffect(() => {
        if (planFingerprint !== prevFingerprint.current) {
            clearGeometryCache();
            prevFingerprint.current = planFingerprint;
        }
    }, [planFingerprint]);

    // Fetch road geometries for visible plans.
    useEffect(() => {
        if (plans.length === 0) {
            setGeometries(new Map());
            return;
        }

        const id = ++fetchIdRef.current;
        fetchAllLegGeometries(plans, visiblePlanIds).then((geoMap) => {
            // Only apply if this is still the latest request.
            if (id === fetchIdRef.current) setGeometries(geoMap);
        });
    }, [plans, visiblePlanIds]);

    // ---- Markers ------------------------------------------------------------
    const storeMarkers = useMemo(() => {
        const seen = new Map();
        shipments.forEach((s) => {
            const store = s.store;
            if (store?.lat != null && !seen.has(store.store_id)) {
                seen.set(store.store_id, { store, shipment: s });
            }
        });
        return [...seen.values()];
    }, [shipments]);

    return (
        <div className="map-wrap">
            <MapContainer center={center} zoom={11} scrollWheelZoom>
                <TileLayer
                    attribution="&copy; OpenStreetMap contributors"
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />

                {warehouse && (
                    <Marker
                        position={[warehouse.lat, warehouse.lon]}
                        icon={warehouseIcon()}
                    >
                        <Popup>
                            <strong>{warehouse.name}</strong>
                            <br />
                            {warehouse.address}
                        </Popup>
                        <Tooltip>{warehouse.name}</Tooltip>
                    </Marker>
                )}

                {storeMarkers.map(({ store, shipment }) => (
                    <Marker
                        key={store.store_id}
                        position={[store.lat, store.lon]}
                        icon={shopIcon()}
                    >
                        <Tooltip>
                            <strong>{store.store_name}</strong>
                            <br />
                            {shipment.weight_kg} kg · {shipment.priority}
                            <br />
                            Window {shipment.earliest_delivery_time}–
                            {shipment.latest_delivery_time}
                        </Tooltip>
                    </Marker>
                ))}

                {plans
                    .filter((p) => visiblePlanIds.has(p.plan_id))
                    .map((plan) => {
                        const isSelected = plan.plan_id === selectedPlanId;
                        const color = planColor(plan.plan_name);
                        const opacity =
                            !selectedPlanId || isSelected ? 0.9 : 0.25;
                        const weight = isSelected ? 6 : 4;
                        return plan.routes.flatMap((route) =>
                            (route.legs || []).map((leg, idx) => {
                                const geoKey = `${plan.plan_id}-${route.vehicle_id}-${idx}`;
                                // Use OSRM road geometry when available,
                                // otherwise fall back to straight line.
                                const positions = geometries.get(geoKey) || [
                                    [leg.from_lat, leg.from_lon],
                                    [leg.to_lat, leg.to_lon],
                                ];
                                return (
                                    <Polyline
                                        key={geoKey}
                                        positions={positions}
                                        pathOptions={{ color, weight, opacity }}
                                        eventHandlers={{
                                            mouseover: (e) =>
                                                e.target.setStyle({
                                                    weight: weight + 3,
                                                }),
                                            mouseout: (e) =>
                                                e.target.setStyle({ weight }),
                                        }}
                                    >
                                        <Tooltip sticky>
                                            <strong>{plan.plan_name}</strong> ·{" "}
                                            {route.vehicle_id}
                                            <br />
                                            {leg.from_name} → {leg.to_name}
                                            <br />
                                            {leg.distance_km} km ·{" "}
                                            {leg.duration_min} min · ETA {leg.eta}
                                        </Tooltip>
                                    </Polyline>
                                );
                            }),
                        );
                    })}
            </MapContainer>
        </div>
    );
}
