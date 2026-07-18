import { PackageIcon, TruckIcon, CloudIcon } from "../Icons";

const priorityBadge = (priority) => {
    if (priority === "high") return "badge badge-critical";
    if (priority === "normal") return "badge badge-info";
    return "badge badge-success";
};

/**
 * Route Planner sidebar: today's shipments, available fleet, and current
 * weather per delivery zone. Pure presentational — data is fetched by the page.
 */
export default function ShipmentSidebar({ shipments, fleet, weather }) {
    return (
        <div className="sidebar">
            <div className="sidebar-section">
                <h3>
                    <PackageIcon /> Today&apos;s Shipments
                    <span
                        className="text-muted"
                        style={{ marginLeft: "auto", fontSize: "0.8rem" }}
                    >
                        {shipments.length}
                    </span>
                </h3>
                <ul className="sidebar-list">
                    {shipments.map((s) => (
                        <li key={s.shipment_id}>
                            <div className="row-title">
                                <span>{s.store?.store_name || s.store_id}</span>
                                <span className={priorityBadge(s.priority)}>
                                    {s.priority}
                                </span>
                            </div>
                            <div className="row-sub">
                                {s.weight_kg} kg · window{" "}
                                {s.earliest_delivery_time}–
                                {s.latest_delivery_time}
                            </div>
                        </li>
                    ))}
                    {shipments.length === 0 && (
                        <li className="text-muted">No shipments loaded.</li>
                    )}
                </ul>
            </div>

            <div className="sidebar-section">
                <h3>
                    <TruckIcon /> Available Fleet
                    <span
                        className="text-muted"
                        style={{ marginLeft: "auto", fontSize: "0.8rem" }}
                    >
                        {fleet.length}
                    </span>
                </h3>
                <ul className="sidebar-list">
                    {fleet.map((v) => (
                        <li key={v.vehicle_id}>
                            <div className="row-title">
                                <span>{v.vehicle_id}</span>
                                <span className="text-muted">
                                    {v.capacity_kg} kg
                                </span>
                            </div>
                            <div className="row-sub">
                                {v.type || v.vehicle_type} ·{" "}
                                {v.driver?.name || "Unassigned"}
                            </div>
                        </li>
                    ))}
                    {fleet.length === 0 && (
                        <li className="text-muted">No available vehicles.</li>
                    )}
                </ul>
            </div>

            <div className="sidebar-section">
                <h3>
                    <CloudIcon /> Weather by Zone
                </h3>
                <ul className="sidebar-list">
                    {weather.map((w, i) => (
                        <li key={w.zone || i}>
                            <div className="row-title">
                                <span>{w.zone}</span>
                                <span className="text-muted">
                                    {w.temperature_c != null
                                        ? `${w.temperature_c}°C`
                                        : ""}
                                </span>
                            </div>
                            <div className="row-sub">
                                {w.condition ||
                                    w.weather_condition ||
                                    w.description ||
                                    "—"}
                            </div>
                        </li>
                    ))}
                    {weather.length === 0 && (
                        <li className="text-muted">No weather data.</li>
                    )}
                </ul>
            </div>
        </div>
    );
}
