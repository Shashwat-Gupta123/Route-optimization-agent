import { createContext, useContext, useEffect, useRef } from "react";
import useAlerts from "../hooks/useAlerts";
import { useToast } from "./Toast";

const AlertsContext = createContext(null);

/**
 * Provides a single shared alerts poll for the whole app (bell badge + panel +
 * monitoring page), so alerts aren't polled multiple times. Also raises a toast
 * whenever a new unacknowledged alert appears since the last poll.
 */
export function AlertsProvider({ children }) {
    const alertsApi = useAlerts(15000);
    const { push } = useToast();
    const knownIds = useRef(null);

    const { alerts } = alertsApi;
    useEffect(() => {
        if (!alerts) return;
        const currentIds = new Set(alerts.map((a) => a.alert_id));
        if (knownIds.current === null) {
            knownIds.current = currentIds;
            return;
        }
        const fresh = alerts.filter(
            (a) => !knownIds.current.has(a.alert_id) && !a.acknowledged,
        );
        fresh.forEach((a) => {
            const variant =
                a.severity === "critical"
                    ? "critical"
                    : a.severity === "warning"
                      ? "warning"
                      : "info";
            push(a.message, variant, 6000);
        });
        knownIds.current = currentIds;
    }, [alerts, push]);

    return (
        <AlertsContext.Provider value={alertsApi}>
            {children}
        </AlertsContext.Provider>
    );
}

export function useAlertsContext() {
    const ctx = useContext(AlertsContext);
    if (!ctx) {
        throw new Error("useAlertsContext must be used within AlertsProvider");
    }
    return ctx;
}
