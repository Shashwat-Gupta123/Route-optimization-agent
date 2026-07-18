import {
    createContext,
    useContext,
    useState,
    useCallback,
    useRef,
} from "react";

const ToastContext = createContext(null);

/**
 * Lightweight app-wide toast/banner system. Wrap the app once; call useToast()
 * anywhere to push a transient notification (used for new alerts, report-sent
 * confirmations, etc.).
 */
export function ToastProvider({ children }) {
    const [toasts, setToasts] = useState([]);
    const idRef = useRef(0);

    const push = useCallback((message, variant = "info", ttl = 4000) => {
        const id = ++idRef.current;
        setToasts((prev) => [...prev, { id, message, variant }]);
        if (ttl) {
            setTimeout(() => {
                setToasts((prev) => prev.filter((t) => t.id !== id));
            }, ttl);
        }
    }, []);

    return (
        <ToastContext.Provider value={{ push }}>
            {children}
            <div className="toast-stack">
                {toasts.map((t) => (
                    <div key={t.id} className={`toast toast-${t.variant}`}>
                        {t.message}
                    </div>
                ))}
            </div>
        </ToastContext.Provider>
    );
}

export function useToast() {
    const ctx = useContext(ToastContext);
    if (!ctx) {
        return { push: () => {} };
    }
    return ctx;
}
