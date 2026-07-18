const fmt = (n, d = 1) =>
    n == null
        ? "—"
        : Number(n).toLocaleString("en-IN", { maximumFractionDigits: d });

/**
 * Before/after comparison for a re-optimization preview, with a Confirm action.
 */
export default function ReoptimizeComparison({
    preview,
    onConfirm,
    onCancel,
    confirming,
}) {
    if (!preview) return null;
    const { before, after } = preview;

    const delta = (a, b) => {
        const diff = (b ?? 0) - (a ?? 0);
        const sign = diff > 0 ? "+" : "";
        return `${sign}${fmt(diff)}`;
    };

    return (
        <div className="chart-card">
            <div className="flex-between" style={{ marginBottom: 12 }}>
                <h3 style={{ margin: 0 }}>Re-optimization Preview</h3>
                <span className="text-muted" style={{ fontSize: "0.8rem" }}>
                    {preview.plan_id}
                </span>
            </div>

            <div className="compare-grid">
                <div className="compare-col">
                    <h4>Current remaining route</h4>
                    <div className="compare-metric">
                        <span>Distance</span>
                        <span>{fmt(before.distance_km)} km</span>
                    </div>
                    <div className="compare-metric">
                        <span>Duration</span>
                        <span>{fmt(before.duration_min, 0)} min</span>
                    </div>
                    <div className="compare-metric">
                        <span>Stops</span>
                        <span>{before.stop_count}</span>
                    </div>
                </div>
                <div
                    className="compare-col"
                    style={{ borderColor: "var(--color-primary)" }}
                >
                    <h4>Re-optimized route</h4>
                    <div className="compare-metric">
                        <span>Distance</span>
                        <span>
                            {fmt(after.distance_km)} km{" "}
                            <span className="text-muted">
                                ({delta(before.distance_km, after.distance_km)})
                            </span>
                        </span>
                    </div>
                    <div className="compare-metric">
                        <span>Duration</span>
                        <span>
                            {fmt(after.duration_min, 0)} min{" "}
                            <span className="text-muted">
                                (
                                {delta(before.duration_min, after.duration_min)}
                                )
                            </span>
                        </span>
                    </div>
                    <div className="compare-metric">
                        <span>Stops</span>
                        <span>{after.stop_count}</span>
                    </div>
                </div>
            </div>

            {after.affected_stores?.length > 0 && (
                <p
                    className="text-muted"
                    style={{ fontSize: "0.82rem", marginTop: 10 }}
                >
                    Affected stores: {after.affected_stores.join(", ")}
                </p>
            )}

            <div style={{ display: "flex", gap: 10, marginTop: 14 }}>
                <button
                    className="btn btn-primary btn-sm"
                    onClick={onConfirm}
                    disabled={confirming}
                >
                    {confirming ? "Confirming…" : "Confirm & Notify Stores"}
                </button>
                <button
                    className="btn btn-ghost btn-sm"
                    onClick={onCancel}
                    disabled={confirming}
                >
                    Cancel
                </button>
            </div>
        </div>
    );
}
