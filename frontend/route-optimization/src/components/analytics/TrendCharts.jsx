import {
    LineChart,
    Line,
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
} from "recharts";

const RED = "#d6001c";
const GRAY = "#9ca3af";
const BORDER = "#e5e5e5";

const axisProps = {
    stroke: "#6b6b6b",
    fontSize: 12,
    tickLine: false,
};

/**
 * Trend charts: distance & fuel cost (planned vs actual), on-time % over time,
 * and vehicle utilization %. The MAQ red is the primary/"actual" series; planned
 * comparison lines use neutral gray.
 */
export default function TrendCharts({ series }) {
    const data = series || [];

    return (
        <div className="chart-grid">
            <div className="chart-card">
                <h3>Distance: Planned vs Actual (km)</h3>
                <ResponsiveContainer width="100%" height={240}>
                    <LineChart data={data}>
                        <CartesianGrid stroke={BORDER} vertical={false} />
                        <XAxis dataKey="date" {...axisProps} />
                        <YAxis {...axisProps} />
                        <Tooltip />
                        <Legend />
                        <Line
                            type="monotone"
                            dataKey="distance_actual_km"
                            name="Actual"
                            stroke={RED}
                            strokeWidth={2.5}
                            dot={false}
                        />
                        <Line
                            type="monotone"
                            dataKey="distance_planned_km"
                            name="Planned"
                            stroke={GRAY}
                            strokeWidth={2}
                            strokeDasharray="5 4"
                            dot={false}
                        />
                    </LineChart>
                </ResponsiveContainer>
            </div>

            <div className="chart-card">
                <h3>Fuel Cost: Planned vs Actual (₹)</h3>
                <ResponsiveContainer width="100%" height={240}>
                    <LineChart data={data}>
                        <CartesianGrid stroke={BORDER} vertical={false} />
                        <XAxis dataKey="date" {...axisProps} />
                        <YAxis {...axisProps} />
                        <Tooltip />
                        <Legend />
                        <Line
                            type="monotone"
                            dataKey="fuel_cost_actual_inr"
                            name="Actual"
                            stroke={RED}
                            strokeWidth={2.5}
                            dot={false}
                        />
                        <Line
                            type="monotone"
                            dataKey="fuel_cost_planned_inr"
                            name="Planned"
                            stroke={GRAY}
                            strokeWidth={2}
                            strokeDasharray="5 4"
                            dot={false}
                        />
                    </LineChart>
                </ResponsiveContainer>
            </div>

            <div className="chart-card">
                <h3>On-time Delivery % Over Time</h3>
                <ResponsiveContainer width="100%" height={240}>
                    <LineChart data={data}>
                        <CartesianGrid stroke={BORDER} vertical={false} />
                        <XAxis dataKey="date" {...axisProps} />
                        <YAxis domain={[0, 100]} {...axisProps} />
                        <Tooltip />
                        <Line
                            type="monotone"
                            dataKey="on_time_pct"
                            name="On-time %"
                            stroke={RED}
                            strokeWidth={2.5}
                            dot={{ r: 3 }}
                        />
                    </LineChart>
                </ResponsiveContainer>
            </div>

            <div className="chart-card">
                <h3>Vehicle Utilization % Over Time</h3>
                <ResponsiveContainer width="100%" height={240}>
                    <BarChart data={data}>
                        <CartesianGrid stroke={BORDER} vertical={false} />
                        <XAxis dataKey="date" {...axisProps} />
                        <YAxis domain={[0, 100]} {...axisProps} />
                        <Tooltip />
                        <Bar
                            dataKey="vehicle_utilization_pct"
                            name="Utilization %"
                            fill={RED}
                            radius={[4, 4, 0, 0]}
                        />
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}
