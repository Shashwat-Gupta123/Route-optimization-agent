import { useCallback, useEffect, useMemo, useState } from "react";
import {
    getWarehouse,
    getShipments,
    getRoutePlan,
    getVehicleLocations,
    reoptimize,
    confirmReoptimize,
} from "../api/endpoints";
import usePolling from "../hooks/usePolling";
import { useToast } from "../components/Toast";
import { useAlertsContext } from "../components/AlertsProvider";
import { STATUS_COLORS } from "../components/mapUtils";
import VehicleMap from "../components/monitoring/VehicleMap";
import DisruptionControls from "../components/monitoring/DisruptionControls";
import ReoptimizeComparison from "../components/monitoring/ReoptimizeComparison";

function statusColor(v) {
    if (v.status === "breakdown" || v.status === "maintenance")
        return STATUS_COLORS.breakdown;
    if (v.status === "delayed" || (v.eta_deviation_min || 0) > 0)
        return STATUS_COLORS.delayed;
    if (v.status === "completed") return STATUS_COLORS.completed;
    return STATUS_COLORS.on_route;
}

/**
 * Component 2 — Live Monitoring page. Polls simulated vehicle positions, offers
 * demo disruption controls, and lets the manager re-optimize a disrupted
 * vehicle's remaining route (preview → confirm).
 */
export default function LiveMonitoring() {
    const { push } = useToast();
    const { refresh: refreshAlerts } = useAlertsContext();

    const [warehouse, setWarehouse] = useState(null);
    const [routePlan, setRoutePlan] = useState(null);
    const [storeById, setStoreById] = useState({});
    const [storeList, setStoreList] = useState([]);
    const [error, setError] = useState(null);

    const [preview, setPreview] = useState(null);
    const [reoptBusy, setReoptBusy] = useState(false);
    const [confirming, setConfirming] = useState(false);

    const fetchVehicles = useCallback(() => getVehicleLocations(), []);
    const { data: vehicleFeed, refresh: refreshVehicles } = usePolling(
        fetchVehicles,
        10000,
    );
    const vehicles = vehicleFeed?.vehicles || [];

    useEffect(() => {
        Promise.allSettled([
            getWarehouse(),
            getRoutePlan(),
            getShipments(),
        ]).then(([wh, rp, sh]) => {
            if (wh.status === "fulfilled") setWarehouse(wh.value);
            if (rp.status === "fulfilled") setRoutePlan(rp.value);
            if (sh.status === "fulfilled") {
                const map = {};
                const list = [];
                (sh.value || []).forEach((s) => {
                    if (s.store && !map[s.store.store_id]) {
                        map[s.store.store_id] = s.store;
                        list.push(s.store);
                    }
                });
                setStoreById(map);
                setStoreList(list);
            }
        });
    }, []);

    const handleAction = (result) => {
        if (result?.message)
            push(
                result.message,
                result.alert?.severity === "critical" ? "critical" : "success",
            );
        refreshVehicles();
        refreshAlerts();
    };

    const handleReoptimize = async (vehicleId) => {
        setReoptBusy(true);
        setError(null);
        try {
            const data = await reoptimize({ vehicle_id: vehicleId });
            setPreview(data);
            push("Re-optimization preview ready.", "success");
        } catch (err) {
            setError(err);
        } finally {
            setReoptBusy(false);
        }
    };

    const handleConfirm = async () => {
        if (!preview) return;
        setConfirming(true);
        try {
            const result = await confirmReoptimize(preview.plan_id);
            push(result.message || "Re-optimization confirmed.", "success");
            setPreview(null);
            refreshVehicles();
            refreshAlerts();
            getRoutePlan()
                .then(setRoutePlan)
                .catch(() => {});
        } catch (err) {
            setError(err);
        } finally {
            setConfirming(false);
        }
    };

    const disruptedIds = useMemo(
        () =>
            new Set(
                vehicles
                    .filter(
                        (v) =>
                            v.status === "breakdown" ||
                            v.status === "delayed" ||
                            (v.eta_deviation_min || 0) > 0,
                    )
                    .map((v) => v.vehicle_id),
            ),
        [vehicles],
    );

    return (
        <main className="page">
            <div className="page-header">
                <h1>Live Monitoring</h1>
                <div className="subtitle">
                    Track vehicles in real time, simulate disruptions, and
                    re-optimize remaining routes.
                    {vehicleFeed?.last_updated && (
                        <span className="text-muted">
                            {" "}
                            · Updated{" "}
                            {new Date(
                                vehicleFeed.last_updated,
                            ).toLocaleTimeString("en-IN")}
                        </span>
                    )}
                </div>
            </div>

            {error && <div className="error-banner">{error.message}</div>}

            <div className="planner-layout">
                <div className="sidebar">
                    <div className="sidebar-section">
                        <h3>Vehicles</h3>
                        <ul
                            className="sidebar-list"
                            style={{ maxHeight: "none" }}
                        >
                            {vehicles.map((v) => (
                                <li key={v.vehicle_id}>
                                    <div className="row-title">
                                        <span>
                                            <span
                                                className="status-dot"
                                                style={{
                                                    background: statusColor(v),
                                                }}
                                            />
                                            {v.vehicle_id}
                                        </span>
                                        <span
                                            className="text-muted"
                                            style={{
                                                textTransform: "capitalize",
                                            }}
                                        >
                                            {v.status}
                                        </span>
                                    </div>
                                    <div className="row-sub">
                                        {v.driver_name || "—"} ·{" "}
                                        {v.current_speed_kmph} km/h · dev{" "}
                                        {v.eta_deviation_min || 0} min
                                    </div>
                                    {disruptedIds.has(v.vehicle_id) && (
                                        <button
                                            className="btn btn-primary btn-sm"
                                            style={{ marginTop: 8 }}
                                            disabled={reoptBusy}
                                            onClick={() =>
                                                handleReoptimize(v.vehicle_id)
                                            }
                                        >
                                            {reoptBusy
                                                ? "Working…"
                                                : "Re-optimize Now"}
                                        </button>
                                    )}
                                </li>
                            ))}
                            {vehicles.length === 0 && (
                                <li className="text-muted">No vehicle data.</li>
                            )}
                        </ul>
                    </div>

                    <div className="sidebar-section">
                        <DisruptionControls
                            vehicles={vehicles}
                            stores={storeList}
                            onAction={handleAction}
                            onError={setError}
                        />
                    </div>
                </div>

                <div className="stack-gap">
                    <VehicleMap
                        warehouse={warehouse}
                        vehicles={vehicles}
                        routePlan={routePlan}
                        stores={storeById}
                    />
                    {preview && (
                        <ReoptimizeComparison
                            preview={preview}
                            confirming={confirming}
                            onConfirm={handleConfirm}
                            onCancel={() => setPreview(null)}
                        />
                    )}
                </div>
            </div>
        </main>
    );
}
