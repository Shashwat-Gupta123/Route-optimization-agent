import {
    PackageIcon,
    ClockIcon,
    RouteIcon,
    CoinIcon,
    LeafIcon,
    GaugeIcon,
    TruckIcon,
} from "../Icons";

const fmt = (n, d = 0) =>
    n == null
        ? "—"
        : Number(n).toLocaleString("en-IN", { maximumFractionDigits: d });

function KpiCard({ icon, label, value, sub, accent }) {
    return (
        <div className="kpi-card">
            <div className="kpi-label">
                {icon} {label}
            </div>
            <div className={`kpi-value ${accent ? "kpi-accent" : ""}`}>
                {value}
            </div>
            {sub && <div className="kpi-sub">{sub}</div>}
        </div>
    );
}

/**
 * KPI summary cards row for the Analytics Dashboard. `summary` is the
 * GET /api/kpis/summary payload.
 */
export default function KpiCards({ summary }) {
    if (!summary) return null;
    const t = summary.totals;
    const eta = summary.eta_accuracy;

    return (
        <div className="kpi-grid">
            <KpiCard
                icon={<PackageIcon />}
                label="Shipments Delivered"
                value={fmt(t.shipments_delivered)}
                sub={`over ${summary.days} day(s)`}
                accent
            />
            <KpiCard
                icon={<ClockIcon />}
                label="On-time Delivery"
                value={`${fmt(t.on_time_pct, 1)}%`}
                sub="average across range"
            />
            <KpiCard
                icon={<RouteIcon />}
                label="Distance (Planned / Actual)"
                value={`${fmt(t.total_distance_actual_km)} km`}
                sub={`planned ${fmt(t.total_distance_planned_km)} km`}
            />
            <KpiCard
                icon={<CoinIcon />}
                label="Fuel Cost (Planned / Actual)"
                value={`₹${fmt(t.total_fuel_cost_actual_inr)}`}
                sub={`planned ₹${fmt(t.total_fuel_cost_planned_inr)}`}
            />
            <KpiCard
                icon={<LeafIcon />}
                label="CO₂ Emissions"
                value={`${fmt(t.total_co2_emissions_kg, 1)} kg`}
            />
            <KpiCard
                icon={<CoinIcon />}
                label="Avg Cost / Delivery"
                value={`₹${fmt(t.avg_cost_per_delivery_inr, 1)}`}
            />
            <KpiCard
                icon={<GaugeIcon />}
                label="Avg Vehicle Utilization"
                value={`${fmt(t.avg_vehicle_utilization_pct, 1)}%`}
            />
            <KpiCard
                icon={<TruckIcon />}
                label="ETA Accuracy"
                value={`${fmt(eta.accuracy_pct, 1)}%`}
                sub={`est ${fmt(eta.estimated_duration_min)} vs actual ${fmt(eta.actual_duration_min)} min (Δ ${fmt(eta.delta_min)})`}
            />
        </div>
    );
}
