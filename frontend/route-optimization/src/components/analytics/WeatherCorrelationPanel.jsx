import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Cell,
    ResponsiveContainer,
} from "recharts";

// Delay severity coloring: <=0 healthy (success), small (warning), large (red).
function barColor(delay) {
    if (delay <= 0) return "#1e8e3e";
    if (delay < 20) return "#d97706";
    return "#d6001c";
}

/**
 * Weather correlation: average delay (actual − planned duration) grouped by
 * weather condition. `data` is GET /api/kpis/weather-correlation payload.
 */
export default function WeatherCorrelationPanel({ data }) {
    const rows = data?.correlation || [];

    return (
        <div className="chart-card">
            <h3>Weather Impact on Delay</h3>
            <ResponsiveContainer width="100%" height={260}>
                <BarChart data={rows} layout="vertical" margin={{ left: 10 }}>
                    <CartesianGrid stroke="#e5e5e5" horizontal={false} />
                    <XAxis
                        type="number"
                        stroke="#6b6b6b"
                        fontSize={12}
                        tickLine={false}
                        unit=" min"
                    />
                    <YAxis
                        type="category"
                        dataKey="weather_condition"
                        stroke="#6b6b6b"
                        fontSize={12}
                        tickLine={false}
                        width={70}
                        style={{ textTransform: "capitalize" }}
                    />
                    <Tooltip formatter={(v) => `${v} min avg delay`} />
                    <Bar
                        dataKey="avg_delay_min"
                        name="Avg delay"
                        radius={[0, 4, 4, 0]}
                    >
                        {rows.map((r) => (
                            <Cell
                                key={r.weather_condition}
                                fill={barColor(r.avg_delay_min)}
                            />
                        ))}
                    </Bar>
                </BarChart>
            </ResponsiveContainer>
            <p
                className="text-muted"
                style={{ fontSize: "0.82rem", textAlign: "center" }}
            >
                Average extra minutes vs planned duration, by weather condition.
            </p>
        </div>
    );
}
