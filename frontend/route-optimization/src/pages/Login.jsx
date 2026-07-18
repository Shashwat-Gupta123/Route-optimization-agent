import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import AuthLayout from "./auth/AuthLayout";
import { RouteIcon } from "../components/Icons";

/**
 * Login page. Validates input, surfaces loading/error states, and redirects to
 * the originally requested protected route (or the dashboard) on success.
 */
export default function Login() {
    const { login } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const redirectTo = location.state?.from?.pathname || "/planner";

    const [form, setForm] = useState({ email: "", password: "" });
    const [errors, setErrors] = useState({});
    const [submitError, setSubmitError] = useState("");
    const [loading, setLoading] = useState(false);
    const [showLoader, setShowLoader] = useState(false);

    const update = (field) => (e) => {
        setForm((f) => ({ ...f, [field]: e.target.value }));
        setErrors((prev) => ({ ...prev, [field]: undefined }));
        setSubmitError("");
    };

    const validate = () => {
        const next = {};
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) {
            next.email = "Enter a valid email address.";
        }
        if (!form.password) {
            next.password = "Password is required.";
        }
        setErrors(next);
        return Object.keys(next).length === 0;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!validate()) return;
        setLoading(true);
        setSubmitError("");
        try {
            await login(form);
            setShowLoader(true);
            setTimeout(() => {
                navigate(redirectTo, { replace: true });
            }, 3000);
        } catch (err) {
            setSubmitError(err.message || "Unable to sign in.");
            setLoading(false);
        }
    };

    if (showLoader) {
        return (
            <div className="fullscreen-loader">
                <div className="loader-content">
                    <RouteIcon size={64} className="loader-icon" />
                    <h2>Optimizing Routes...</h2>
                    <p>Computing the best path for fast truck delivery</p>
                    <div className="loader-progress-bar">
                        <div className="loader-progress-fill"></div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <AuthLayout
            title="Welcome back"
            subtitle="Sign in to your dispatch console"
            footer={
                <span>
                    New to Route Optimizer?{" "}
                    <Link to="/signup">Create an account</Link>
                </span>
            }
        >
            <form className="auth-form" onSubmit={handleSubmit} noValidate>
                {submitError && (
                    <div className="error-banner">{submitError}</div>
                )}

                <div className="form-row">
                    <label htmlFor="email">Email</label>
                    <input
                        id="email"
                        type="email"
                        autoComplete="email"
                        value={form.email}
                        onChange={update("email")}
                        placeholder="you@warehouse.com"
                        aria-invalid={!!errors.email}
                    />
                    {errors.email && (
                        <span className="field-error">{errors.email}</span>
                    )}
                </div>

                <div className="form-row">
                    <label htmlFor="password">Password</label>
                    <input
                        id="password"
                        type="password"
                        autoComplete="current-password"
                        value={form.password}
                        onChange={update("password")}
                        placeholder="Enter your password"
                        aria-invalid={!!errors.password}
                    />
                    {errors.password && (
                        <span className="field-error">{errors.password}</span>
                    )}
                </div>

                <button
                    type="submit"
                    className="btn btn-primary auth-submit"
                    disabled={loading}
                >
                    {loading ? <span className="spinner" /> : null}
                    {loading ? "Signing in…" : "Sign in"}
                </button>
            </form>
        </AuthLayout>
    );
}
