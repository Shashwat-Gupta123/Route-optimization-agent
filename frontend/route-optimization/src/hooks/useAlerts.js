import { useCallback } from "react";
import client from "../api/client";
import usePolling from "./usePolling";

/**
 * Shared alerts hook used by the AppShell bell + Live Monitoring page. Polls
 * GET /api/alerts every 15s and exposes the list, the unacknowledged count, and
 * an acknowledge action that refreshes the list on success.
 */
export default function useAlerts(intervalMs = 15000) {
    const fetcher = useCallback(async () => {
        const { data } = await client.get("/api/alerts");
        return data;
    }, []);

    const { data, error, loading, refresh } = usePolling(fetcher, intervalMs);
    const alerts = Array.isArray(data) ? data : [];
    const unacknowledgedCount = alerts.filter((a) => !a.acknowledged).length;

    const acknowledge = useCallback(
        async (alertId) => {
            await client.post(`/api/alerts/${alertId}/acknowledge`);
            await refresh();
        },
        [refresh],
    );

    return {
        alerts,
        unacknowledgedCount,
        error,
        loading,
        refresh,
        acknowledge,
    };
}
