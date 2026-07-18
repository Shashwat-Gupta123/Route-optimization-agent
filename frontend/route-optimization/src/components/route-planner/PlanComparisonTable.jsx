import { planColor } from "./RouteMap";

const fmt = (n, digits = 1) =>
    n == null
        ? "—"
        : Number(n).toLocaleString("en-IN", { maximumFractionDigits: digits });

/**
 * Comparison table: one row per plan with distance/duration/cost/emissions/score.
 * Clicking a row selects that plan (highlights it on the map, dims the others).
 */
export default function PlanComparisonTable({
    plans,
    selectedPlanId,
    onSelect,
}) {
    return (
        <div className="chart-card" style={{ padding: 0, overflow: "hidden" }}>
            <table className="data-table">
                <thead>
                    <tr>
                        <th>Plan</th>
                        <th>Distance</th>
                        <th>Duration</th>
                        <th>Fuel cost</th>
                        <th>Emissions</th>
                        <th>On-time</th>
                        <th>Score</th>
                    </tr>
                </thead>
                <tbody>
                    {plans.map((p) => {
                        const t = p.totals || {};
                        return (
                            <tr
                                key={p.plan_id}
                                className={
                                    p.plan_id === selectedPlanId
                                        ? "selected"
                                        : ""
                                }
                                onClick={() => onSelect(p.plan_id)}
                            >
                                <td>
                                    <span
                                        className="plan-swatch"
                                        style={{
                                            background: planColor(p.plan_name),
                                            marginRight: 8,
                                        }}
                                    />
                                    <span
                                        style={{ textTransform: "capitalize" }}
                                    >
                                        {p.plan_name}
                                    </span>
                                </td>
                                <td>{fmt(t.total_distance_km)} km</td>
                                <td>{fmt(t.total_duration_min, 0)} min</td>
                                <td>₹{fmt(t.total_fuel_cost_inr)}</td>
                                <td>{fmt(t.total_co2_emissions_kg)} kg</td>
                                <td>{fmt(t.on_time_pct, 0)}%</td>
                                <td>
                                    <strong>
                                        {fmt(p.effectiveness_score)}
                                    </strong>
                                </td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
    );
}
