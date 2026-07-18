import { useCallback, useEffect, useState } from "react";
import {
    getKpiSummary,
    getKpiTrends,
    getCostBreakdown,
    getWeatherCorrelation,
    sendReport,
} from "../api/endpoints";
import { useToast } from "../components/Toast";
import { useAlertsContext } from "../components/AlertsProvider";
import { ChartIcon } from "../components/Icons";
import KpiCards from "../components/analytics/KpiCards";
import TrendCharts from "../components/analytics/TrendCharts";
import CostBreakdownChart from "../components/analytics/CostBreakdownChart";
import WeatherCorrelationPanel from "../components/analytics/WeatherCorrelationPanel";

function isoDaysAgo(days) {
    const d = new Date();
    d.setDate(d.getDate() - days);
    return d.toISOString().slice(0, 10);
}

/**
 * Component 3 — Analytics Dashboard. Date-range-driven KPI cards, trend charts,
 * cost breakdown, weather correlation, plus a "Send Weekly Report" action.
 */
export default function AnalyticsDashboard() {
    const { push } = useToast();
    const { refresh: refreshAlerts } = useAlertsContext();

    const [from, setFrom] = useState(isoDaysAgo(14));
    const [to, setTo] = useState(isoDaysAgo(0));

    const [summary, setSummary] = useState(null);
    const [trends, setTrends] = useState(null);
    const [costs, setCosts] = useState(null);
    const [weather, setWeather] = useState(null);

    const [loading, setLoading] = useState(false);
    const [sending, setSending] = useState(false);
    const [error, setError] = useState(null);

    const load = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const [s, t, c, w] = await Promise.all([
                getKpiSummary(from, to),
                getKpiTrends(from, to),
                getCostBreakdown(from, to),
                getWeatherCorrelation(),
            ]);
            setSummary(s);
            setTrends(t);
            setCosts(c);
            setWeather(w);
        } catch (err) {
            setError(err);
        } finally {
            setLoading(false);
        }
    }, [from, to]);

    useEffect(() => {
        load();
        // Load once on mount; subsequent loads are user-driven via "Apply".
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const handleSendReport = async () => {
        setSending(true);
        try {
            await sendReport(from, to);
            push("Report sent to dispatch manager.", "success");
            refreshAlerts();
        } catch (err) {
            setError(err);
        } finally {
            setSending(false);
        }
    };

    return (
        <main className="page">
            <div className="page-header flex-between">
                <div>
                    <h1>Analytics Dashboard</h1>
                    <div className="subtitle">
                        Routing performance, cost efficiency and delivery
                        reliability over time.
                    </div>
                </div>
                <button
                    className="btn btn-primary"
                    onClick={handleSendReport}
                    disabled={sending}
                >
                    {sending ? (
                        <span className="spinner" />
                    ) : (
                        <ChartIcon size={16} />
                    )}
                    {sending ? "Sending…" : "Send Weekly Report"}
                </button>
            </div>

            <div className="toolbar">
                <div className="form-row" style={{ marginBottom: 0 }}>
                    <label>From</label>
                    <input
                        type="date"
                        value={from}
                        onChange={(e) => setFrom(e.target.value)}
                    />
                </div>
                <div className="form-row" style={{ marginBottom: 0 }}>
                    <label>To</label>
                    <input
                        type="date"
                        value={to}
                        onChange={(e) => setTo(e.target.value)}
                    />
                </div>
                <button
                    className="btn btn-ghost"
                    onClick={load}
                    disabled={loading}
                >
                    {loading ? "Loading…" : "Apply"}
                </button>
            </div>

            {error && <div className="error-banner">{error.message}</div>}
            {loading && (
                <div className="loading-block">
                    <span className="spinner" /> Loading analytics…
                </div>
            )}

            {!loading && summary && (
                <>
                    <KpiCards summary={summary} />
                    <TrendCharts series={trends?.series} />
                    <div className="chart-grid">
                        <CostBreakdownChart data={costs} />
                        <WeatherCorrelationPanel data={weather} />
                    </div>
                </>
            )}
        </main>
    );
}
