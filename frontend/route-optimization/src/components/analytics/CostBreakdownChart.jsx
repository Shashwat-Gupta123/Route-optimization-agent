import {
    PieChart,
    Pie,
    Cell,
    Tooltip,
    Legend,
    ResponsiveContainer,
} from "recharts";

// Fuel = MAQ red (primary/"the number"), others neutral so red carries meaning.
const COLORS = ["#d6001c", "#9ca3af", "#4b5563"];

const fmt = (n) =>
    Number(n).toLocaleString("en-IN", { maximumFractionDigits: 0 });

/**
 * Cost breakdown pie: fuel vs labour vs vehicle wear share of total cost.
 * `data` is the GET /api/kpis/cost-breakdown payload.
 */
export default function CostBreakdownChart({ data }) {
    if (!data) return null;
    const pieData = data.breakdown || [];

    return (
        <div className="chart-card">
            <h3>Cost Breakdown</h3>
            <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                    <Pie
                        data={pieData}
                        dataKey="value"
                        nameKey="category"
                        innerRadius={55}
                        outerRadius={90}
                        paddingAngle={2}
                        label={(e) => `${e.category} ${e.pct}%`}
                    >
                        {pieData.map((entry, i) => (
                            <Cell
                                key={entry.category}
                                fill={COLORS[i % COLORS.length]}
                            />
                        ))}
                    </Pie>
                    <Tooltip formatter={(v) => `₹${fmt(v)}`} />
                    <Legend />
                </PieChart>
            </ResponsiveContainer>
            <p
                className="text-muted"
                style={{ fontSize: "0.82rem", textAlign: "center" }}
            >
                Total delivery cost: ₹{fmt(data.total_cost_inr)}
            </p>
        </div>
    );
}
