import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

/**
 * Route guard for authenticated areas. While the persisted session is being
 * restored it shows a lightweight loader; unauthenticated users are redirected
 * to /login with the attempted path preserved so they land back where they were
 * headed after signing in.
 */
export default function ProtectedRoute() {
    const { isAuthenticated, initializing } = useAuth();
    const location = useLocation();

    if (initializing) {
        return (
            <div className="route-loading">
                <span className="spinner" /> Loading…
            </div>
        );
    }

    if (!isAuthenticated) {
        return <Navigate to="/login" replace state={{ from: location }} />;
    }

    return <Outlet />;
}
