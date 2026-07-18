import { useMemo } from "react";
import { MapContainer, TileLayer, Marker, Tooltip, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { coloredDot, warehouseIcon, shopIcon, STATUS_COLORS } from "../mapUtils";

function vehicleColor(v) {
    if (v.status === "breakdown" || v.status === "maintenance")
        return STATUS_COLORS.breakdown;
    if (v.status === "completed") return STATUS_COLORS.completed;
    if (v.status === "delayed" || (v.eta_deviation_min || 0) > 0)
        return STATUS_COLORS.delayed;
    return STATUS_COLORS.on_route;
}

/**
 * Live monitoring map: vehicle markers (colored by status) with hover details,
 * plus the approved route's remaining stops (outlined) vs completed (filled).
 */
export default function VehicleMap({ warehouse, vehicles, routePlan, stores }) {
    const center = warehouse ? [warehouse.lat, warehouse.lon] : [28.5, 77.4];

    // Build stop markers from the approved plan, tagging completed vs upcoming.
    const stopMarkers = useMemo(() => {
        if (!routePlan?.routes) return [];
        const storeById = stores || {};
        const markers = [];
        routePlan.routes.forEach((route) => {
            const loc = vehicles.find((v) => v.vehicle_id === route.vehicle_id);
            const lastDone = loc?.last_stop_completed;
            const ids = route.stops.map((s) => s.store_id);
            const doneIdx = lastDone ? ids.indexOf(lastDone) : -1;
            route.stops.forEach((stop, i) => {
                const store = storeById[stop.store_id];
                if (!store?.lat) return;
                markers.push({
                    id: `${route.vehicle_id}-${stop.store_id}`,
                    lat: store.lat,
                    lon: store.lon,
                    name: store.store_name,
                    eta: stop.eta,
                    vehicle: route.vehicle_id,
                    completed: i <= doneIdx,
                });
            });
        });
        return markers;
    }, [routePlan, vehicles, stores]);

    return (
        <div className="map-wrap" style={{ height: 520 }}>
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
                        <Tooltip>{warehouse.name}</Tooltip>
                    </Marker>
                )}

                {stopMarkers.map((m) => (
                    <Marker
                        key={m.id}
                        position={[m.lat, m.lon]}
                        icon={shopIcon({ completed: m.completed })}
                    >
                        <Tooltip>
                            <strong>{m.name}</strong>
                            <br />
                            {m.completed
                                ? "Completed"
                                : `Upcoming · ETA ${m.eta}`}{" "}
                            · {m.vehicle}
                        </Tooltip>
                    </Marker>
                ))}

                {vehicles.map((v) =>
                    v.current_location ? (
                        <Marker
                            key={v.vehicle_id}
                            position={[
                                v.current_location.lat,
                                v.current_location.lon,
                            ]}
                            icon={coloredDot(vehicleColor(v), { size: 20 })}
                        >
                            <Tooltip>
                                <strong>{v.vehicle_id}</strong> · {v.status}
                                <br />
                                {v.driver_name || "Driver —"} ·{" "}
                                {v.current_speed_kmph} km/h
                                <br />
                                Next: {v.next_stop_name || v.next_stop || "—"} ·
                                ETA {v.eta_next_stop || "—"}
                                <br />
                                Deviation: {v.eta_deviation_min || 0} min
                            </Tooltip>
                            <Popup>
                                <strong>{v.vehicle_id}</strong> ({v.status})
                                <br />
                                Driver: {v.driver_name || "—"}
                                <br />
                                Speed: {v.current_speed_kmph} km/h
                                <br />
                                Next stop:{" "}
                                {v.next_stop_name || v.next_stop || "—"}
                            </Popup>
                        </Marker>
                    ) : null,
                )}
            </MapContainer>
        </div>
    );
}
