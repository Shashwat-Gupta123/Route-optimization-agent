import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import "./App.css";
import { AuthProvider } from "./context/AuthContext";
import { ToastProvider } from "./components/Toast";
import { AlertsProvider } from "./components/AlertsProvider";
import ProtectedRoute from "./components/ProtectedRoute";
import AppShell from "./layout/AppShell";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import RoutePlanner from "./pages/RoutePlanner";
import LiveMonitoring from "./pages/LiveMonitoring";
import AnalyticsDashboard from "./pages/AnalyticsDashboard";

/**
 * Authenticated application shell + shared data providers. Toast and Alerts
 * providers live here (not around the whole tree) so their backend polling only
 * runs once a user is signed in — the public auth pages stay lightweight.
 */
function ProtectedApp() {
    return (
        <ToastProvider>
            <AlertsProvider>
                <AppShell />
            </AlertsProvider>
        </ToastProvider>
    );
}

/**
 * App entry: auth-aware router. Public routes (/login, /signup) are open;
 * everything else sits behind ProtectedRoute and renders inside AppShell.
 */
function App() {
    return (
        <AuthProvider>
            <BrowserRouter>
                <Routes>
                    <Route path="/login" element={<Login />} />
                    <Route path="/signup" element={<Signup />} />

                    <Route element={<ProtectedRoute />}>
                        <Route element={<ProtectedApp />}>
                            <Route
                                index
                                element={<Navigate to="/planner" replace />}
                            />
                            <Route path="/planner" element={<RoutePlanner />} />
                            <Route
                                path="/monitoring"
                                element={<LiveMonitoring />}
                            />
                            <Route
                                path="/analytics"
                                element={<AnalyticsDashboard />}
                            />
                            <Route
                                path="*"
                                element={<Navigate to="/planner" replace />}
                            />
                        </Route>
                    </Route>
                </Routes>
            </BrowserRouter>
        </AuthProvider>
    );
}

export default App;
