import { useAlertsContext } from "../components/AlertsProvider";

function severityClass(severity) {
    if (severity === "critical") return "sev-critical";
    if (severity === "warning") return "sev-warning";
    return "sev-info";
}

function badgeClass(severity) {
    if (severity === "critical") return "badge badge-critical";
    if (severity === "warning") return "badge badge-warning";
    return "badge badge-info";
}

function formatTime(iso) {
    if (!iso) return "";
    try {
        return new Date(iso).toLocaleString("en-IN", {
            day: "2-digit",
            month: "short",
            hour: "2-digit",
            minute: "2-digit",
        });
    } catch {
        return iso;
    }
}

/**
 * Shared slide-over alerts panel, mounted once in AppShell and reachable from
 * every page via the header bell. Lists recent alerts (newest first) with a
 * per-alert Acknowledge action.
 */
export default function AlertsPanel({ open, onClose }) {
    const { alerts, loading, error, acknowledge } = useAlertsContext();

    if (!open) return null;

    return (
        <>
            <div className="alerts-overlay" onClick={onClose} />
            <aside className="alerts-panel" role="dialog" aria-label="Alerts">
                <div className="alerts-panel-header">
                    <h3 style={{ margin: 0 }}>Alerts</h3>
                    <button
                        className="close-btn"
                        onClick={onClose}
                        aria-label="Close"
                    >
                        &times;
                    </button>
                </div>
                <div className="alerts-panel-body">
                    {loading && (
                        <div className="loading-block">
                            <span className="spinner" /> Loading alerts…
                        </div>
                    )}
                    {error && (
                        <div className="error-banner">{error.message}</div>
                    )}
                    {!loading && !error && alerts.length === 0 && (
                        <p
                            className="text-muted"
                            style={{ fontSize: "0.85rem" }}
                        >
                            No alerts yet. Simulated disruptions and reports
                            will appear here.
                        </p>
                    )}
                    {alerts.map((a) => (
                        <div
                            key={a.alert_id}
                            className={`alert-item ${severityClass(a.severity)} ${a.acknowledged ? "ack" : ""}`}
                        >
                            <span className={badgeClass(a.severity)}>
                                {a.severity}
                            </span>
                            <p className="alert-msg">{a.message}</p>
                            <div className="alert-meta">
                                <span>{formatTime(a.created_at)}</span>
                                {a.acknowledged ? (
                                    <span className="badge badge-success">
                                        Acknowledged
                                    </span>
                                ) : (
                                    <button
                                        className="btn btn-ghost btn-sm"
                                        onClick={() => acknowledge(a.alert_id)}
                                    >
                                        Acknowledge
                                    </button>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </aside>
        </>
    );
}
