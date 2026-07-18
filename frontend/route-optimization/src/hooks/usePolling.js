import { useEffect, useRef, useState, useCallback } from "react";

/**
 * Generic interval-polling hook. Calls `fetcher` immediately and then every
 * `intervalMs`, returning the latest data plus loading/error state and a manual
 * refresh trigger. Reused across the app (alerts, vehicle locations, etc.) so no
 * component writes its own setInterval logic.
 *
 * @param {() => Promise<any>} fetcher async function returning the data
 * @param {number} intervalMs poll interval in ms; pass 0 to disable polling
 * @param {boolean} enabled when false, polling is paused
 */
export default function usePolling(
    fetcher,
    intervalMs = 15000,
    enabled = true,
) {
    const [data, setData] = useState(null);
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(true);
    const savedFetcher = useRef(fetcher);

    useEffect(() => {
        savedFetcher.current = fetcher;
    }, [fetcher]);

    const refresh = useCallback(async () => {
        try {
            const result = await savedFetcher.current();
            setData(result);
            setError(null);
        } catch (err) {
            setError(err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        if (!enabled) return undefined;
        refresh();
        if (!intervalMs) return undefined;
        const id = setInterval(refresh, intervalMs);
        return () => clearInterval(id);
    }, [refresh, intervalMs, enabled]);

    return { data, error, loading, refresh };
}
