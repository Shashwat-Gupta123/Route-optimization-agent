import { useState } from "react";
import {
    simulateTrafficJam,
    simulateBreakdown,
    addUrgentOrder,
} from "../../api/endpoints";

/**
 * Demo-mode disruption controls: simulate a traffic jam, a breakdown, or inject
 * an urgent order. Clearly labelled as a demo affordance. Calls back to the page
 * (onAction) after each successful action so it can refresh vehicles + alerts.
 */
export default function DisruptionControls({
    vehicles,
    stores,
    onAction,
    onError,
}) {
    const [jamVehicle, setJamVehicle] = useState("");
    const [jamDelay, setJamDelay] = useState(15);
    const [breakdownVehicle, setBreakdownVehicle] = useState("");
    const [order, setOrder] = useState({
        store_id: "",
        weight_kg: 100,
        latest_delivery_time: "13:00",
    });
    const [busy, setBusy] = useState("");

    const run = async (key, fn) => {
        setBusy(key);
        try {
            const result = await fn();
            onAction?.(result);
        } catch (err) {
            onError?.(err);
        } finally {
            setBusy("");
        }
    };

    const vehicleOptions = vehicles.map((v) => v.vehicle_id);
    const storeList = Array.isArray(stores) ? stores : [];

    return (
        <div className="control-panel">
            <div className="demo-banner">
                Demo Controls — Simulate Disruption. These manually trigger
                events that real telematics would normally detect.
            </div>

            <div className="control-block">
                <h4>Simulate Traffic Jam</h4>
                <div className="form-row">
                    <label>Vehicle</label>
                    <select
                        value={jamVehicle}
                        onChange={(e) => setJamVehicle(e.target.value)}
                    >
                        <option value="">Select vehicle…</option>
                        {vehicleOptions.map((id) => (
                            <option key={id} value={id}>
                                {id}
                            </option>
                        ))}
                    </select>
                </div>
                <div className="form-row">
                    <label>Delay (minutes)</label>
                    <input
                        type="number"
                        min="1"
                        value={jamDelay}
                        onChange={(e) => setJamDelay(Number(e.target.value))}
                    />
                </div>
                <button
                    className="btn btn-ghost btn-sm"
                    disabled={!jamVehicle || busy === "jam"}
                    onClick={() =>
                        run("jam", () =>
                            simulateTrafficJam(jamVehicle, jamDelay),
                        )
                    }
                >
                    {busy === "jam" ? "Applying…" : "Apply Traffic Jam"}
                </button>
            </div>

            <div className="control-block">
                <h4>Simulate Breakdown</h4>
                <div className="form-row">
                    <label>Vehicle</label>
                    <select
                        value={breakdownVehicle}
                        onChange={(e) => setBreakdownVehicle(e.target.value)}
                    >
                        <option value="">Select vehicle…</option>
                        {vehicleOptions.map((id) => (
                            <option key={id} value={id}>
                                {id}
                            </option>
                        ))}
                    </select>
                </div>
                <button
                    className="btn btn-ghost btn-sm"
                    disabled={!breakdownVehicle || busy === "breakdown"}
                    onClick={() =>
                        run("breakdown", () =>
                            simulateBreakdown(breakdownVehicle),
                        )
                    }
                >
                    {busy === "breakdown" ? "Marking…" : "Mark Breakdown"}
                </button>
            </div>

            <div className="control-block">
                <h4>Add Urgent Order</h4>
                <div className="form-row">
                    <label>Store</label>
                    <select
                        value={order.store_id}
                        onChange={(e) =>
                            setOrder({ ...order, store_id: e.target.value })
                        }
                    >
                        <option value="">Select store…</option>
                        {storeList.map((s) => (
                            <option key={s.store_id} value={s.store_id}>
                                {s.store_name || s.store_id}
                            </option>
                        ))}
                    </select>
                </div>
                <div className="form-row">
                    <label>Weight (kg)</label>
                    <input
                        type="number"
                        min="1"
                        value={order.weight_kg}
                        onChange={(e) =>
                            setOrder({
                                ...order,
                                weight_kg: Number(e.target.value),
                            })
                        }
                    />
                </div>
                <div className="form-row">
                    <label>Deadline</label>
                    <input
                        type="time"
                        value={order.latest_delivery_time}
                        onChange={(e) =>
                            setOrder({
                                ...order,
                                latest_delivery_time: e.target.value,
                            })
                        }
                    />
                </div>
                <button
                    className="btn btn-ghost btn-sm"
                    disabled={!order.store_id || busy === "order"}
                    onClick={() => run("order", () => addUrgentOrder(order))}
                >
                    {busy === "order" ? "Adding…" : "Add Urgent Order"}
                </button>
            </div>
        </div>
    );
}
