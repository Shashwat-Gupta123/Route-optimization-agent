import { useEffect, useMemo, useState } from "react";
import {
    getWarehouse,
    getShipments,
    getFleet,
    getWeather,
    planRoutes,
    approveRoute,
    resetShipments,
} from "../api/endpoints";
import { useToast } from "../components/Toast";
import { RouteIcon } from "../components/Icons";
import ShipmentSidebar from "../components/route-planner/ShipmentSidebar";
import RouteMap, { planColor } from "../components/route-planner/RouteMap";
import PlanComparisonTable from "../components/route-planner/PlanComparisonTable";

/**
 * Component 1 — Route Planner page. Loads today's shipments/fleet/weather, lets
 * the manager generate the fastest/cheapest/balanced plans, compare them on a
 * map + table, and approve one.
 */
export default function RoutePlanner() {
    const { push } = useToast();

    const [warehouse, setWarehouse] = useState(null);
    const [shipments, setShipments] = useState([]);
    const [fleet, setFleet] = useState([]);
    const [weather, setWeather] = useState([]);

    const [plans, setPlans] = useState([]);
    const [visiblePlanIds, setVisiblePlanIds] = useState(new Set());
    const [selectedPlanId, setSelectedPlanId] = useState(null);

    const [generating, setGenerating] = useState(false);
    const [approving, setApproving] = useState(false);
    const [approved, setApproved] = useState(false);
    const [resetting, setResetting] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        Promise.allSettled([
            getWarehouse(),
            getShipments(),
            getFleet(),
            getWeather(),
        ]).then(([wh, sh, fl, we]) => {
            if (wh.status === "fulfilled") setWarehouse(wh.value);
            if (sh.status === "fulfilled") setShipments(sh.value || []);
            if (fl.status === "fulfilled") setFleet(fl.value || []);
            if (we.status === "fulfilled") setWeather(we.value || []);
            const failed = [wh, sh, fl, we].find(
                (r) => r.status === "rejected",
            );
            if (failed) setError(failed.reason);
        });
    }, []);

    const handleGenerate = async () => {
        setGenerating(true);
        setError(null);
        setApproved(false);
        try {
            const data = await planRoutes();
            const nextPlans = data.plans || [];
            setPlans(nextPlans);
            setVisiblePlanIds(new Set(nextPlans.map((p) => p.plan_id)));
            setSelectedPlanId(nextPlans[0]?.plan_id ?? null);
            if (data.weather?.length) setWeather(data.weather);
            push(`Generated ${nextPlans.length} route plans.`, "success");
        } catch (err) {
            setError(err);
        } finally {
            setGenerating(false);
        }
    };

    const handleApprove = async () => {
        if (!selectedPlanId) return;
        setApproving(true);
        setError(null);
        try {
            await approveRoute(selectedPlanId);
            setApproved(true);
            push("Route plan approved and persisted.", "success");
        } catch (err) {
            setError(err);
        } finally {
            setApproving(false);
        }
    };

    const handleReset = async () => {
        setResetting(true);
        setError(null);
        try {
            const data = await resetShipments();
            // Reload shipments from server so sidebar updates.
            const fresh = await getShipments();
            setShipments(fresh || []);
            // Clear any generated plans since they're now stale.
            setPlans([]);
            setVisiblePlanIds(new Set());
            setSelectedPlanId(null);
            setApproved(false);
            push(data.message || "Shipments reset to pending.", "success");
        } catch (err) {
            setError(err);
        } finally {
            setResetting(false);
        }
    };

    const togglePlan = (planId) => {
        setVisiblePlanIds((prev) => {
            const next = new Set(prev);
            if (next.has(planId)) next.delete(planId);
            else next.add(planId);
            return next;
        });
    };

    const selectedPlan = useMemo(
        () => plans.find((p) => p.plan_id === selectedPlanId) || null,
        [plans, selectedPlanId],
    );

    return (
        <main className="page">
            <div className="page-header flex-between">
                <div>
                    <h1>Route Planner</h1>
                    <div className="subtitle">
                        Generate and compare optimized delivery routes for
                        today&apos;s shipments.
                    </div>
                </div>
                <div style={{ display: "flex", gap: 10 }}>
                    <button
                        className="btn btn-primary"
                        onClick={handleGenerate}
                        disabled={generating}
                    >
                        {generating ? (
                            <span className="spinner" />
                        ) : (
                            <RouteIcon size={16} />
                        )}
                        {generating ? "Generating…" : "Generate Plans"}
                    </button>
                    <button
                        className="btn btn-ghost"
                        onClick={handleApprove}
                        disabled={!selectedPlanId || approving || approved}
                    >
                        {approved
                            ? "Approved ✓"
                            : approving
                              ? "Approving…"
                              : "Approve Route"}
                    </button>
                    <button
                        className="btn btn-ghost"
                        onClick={handleReset}
                        disabled={resetting}
                        title="Reset all shipments to pending so you can re-generate plans"
                        style={{ color: "var(--color-warning, #d97706)" }}
                    >
                        {resetting ? "Resetting…" : "↺ Reset Shipments"}
                    </button>
                </div>
            </div>

            {error && <div className="error-banner">{error.message}</div>}

            <div className="planner-layout">
                <ShipmentSidebar
                    shipments={shipments}
                    fleet={fleet}
                    weather={weather}
                />

                <div className="stack-gap">
                    {plans.length > 0 && (
                        <div className="map-toolbar">
                            {plans.map((p) => (
                                <label key={p.plan_id} className="plan-toggle">
                                    <input
                                        type="checkbox"
                                        checked={visiblePlanIds.has(p.plan_id)}
                                        onChange={() => togglePlan(p.plan_id)}
                                    />
                                    <span
                                        className="plan-swatch"
                                        style={{
                                            background: planColor(p.plan_name),
                                        }}
                                    />
                                    <span
                                        style={{ textTransform: "capitalize" }}
                                    >
                                        {p.plan_name}
                                    </span>
                                </label>
                            ))}
                        </div>
                    )}

                    <RouteMap
                        warehouse={warehouse}
                        shipments={shipments}
                        plans={plans}
                        visiblePlanIds={visiblePlanIds}
                        selectedPlanId={selectedPlanId}
                    />

                    {plans.length > 0 ? (
                        <>
                            <h2
                                className="section-heading"
                                style={{ fontSize: "1.2rem", margin: 0 }}
                            >
                                Plan Comparison
                            </h2>
                            <PlanComparisonTable
                                plans={plans}
                                selectedPlanId={selectedPlanId}
                                onSelect={setSelectedPlanId}
                            />
                            {selectedPlan && (
                                <p
                                    className="text-muted"
                                    style={{ fontSize: "0.85rem" }}
                                >
                                    Selected:{" "}
                                    <strong
                                        style={{ textTransform: "capitalize" }}
                                    >
                                        {selectedPlan.plan_name}
                                    </strong>{" "}
                                    — {selectedPlan.routes.length} vehicle
                                    route(s), effectiveness score{" "}
                                    {selectedPlan.effectiveness_score}.
                                </p>
                            )}
                        </>
                    ) : (
                        !generating && (
                            <p className="text-muted">
                                Click <strong>Generate Plans</strong> to compute
                                route options for today.
                            </p>
                        )
                    )}
                </div>
            </div>
        </main>
    );
}
