import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import AuthLayout from "./auth/AuthLayout";

/**
 * Signup page. Validates name/email/password (with confirmation and a minimum
 * strength rule), handles loading/error states, and signs the new user straight
 * into the dashboard on success.
 */
export default function Signup() {
    const { signup } = useAuth();
    const navigate = useNavigate();

    const [form, setForm] = useState({
        name: "",
        email: "",
        password: "",
        confirm: "",
    });
    const [errors, setErrors] = useState({});
    const [submitError, setSubmitError] = useState("");
    const [loading, setLoading] = useState(false);

    const update = (field) => (e) => {
        setForm((f) => ({ ...f, [field]: e.target.value }));
        setErrors((prev) => ({ ...prev, [field]: undefined }));
        setSubmitError("");
    };

    const validate = () => {
        const next = {};
        if (form.name.trim().length < 2) {
            next.name = "Enter your full name.";
        }
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) {
            next.email = "Enter a valid email address.";
        }
        if (form.password.length < 8) {
            next.password = "Password must be at least 8 characters.";
        }
        if (form.confirm !== form.password) {
            next.confirm = "Passwords do not match.";
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
            await signup(form);
            navigate("/planner", { replace: true });
        } catch (err) {
            setSubmitError(err.message || "Unable to create account.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <AuthLayout
            title="Create your account"
            subtitle="Set up access to the dispatch console"
            footer={
                <span>
                    Already have an account? <Link to="/login">Sign in</Link>
                </span>
            }
        >
            <form className="auth-form" onSubmit={handleSubmit} noValidate>
                {submitError && (
                    <div className="error-banner">{submitError}</div>
                )}

                <div className="form-row">
                    <label htmlFor="name">Full name</label>
                    <input
                        id="name"
                        type="text"
                        autoComplete="name"
                        value={form.name}
                        onChange={update("name")}
                        placeholder="Dispatch Manager"
                        aria-invalid={!!errors.name}
                    />
                    {errors.name && (
                        <span className="field-error">{errors.name}</span>
                    )}
                </div>

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
                        autoComplete="new-password"
                        value={form.password}
                        onChange={update("password")}
                        placeholder="At least 8 characters"
                        aria-invalid={!!errors.password}
                    />
                    {errors.password && (
                        <span className="field-error">{errors.password}</span>
                    )}
                </div>

                <div className="form-row">
                    <label htmlFor="confirm">Confirm password</label>
                    <input
                        id="confirm"
                        type="password"
                        autoComplete="new-password"
                        value={form.confirm}
                        onChange={update("confirm")}
                        placeholder="Re-enter your password"
                        aria-invalid={!!errors.confirm}
                    />
                    {errors.confirm && (
                        <span className="field-error">{errors.confirm}</span>
                    )}
                </div>

                <button
                    type="submit"
                    className="btn btn-primary auth-submit"
                    disabled={loading}
                >
                    {loading ? <span className="spinner" /> : null}
                    {loading ? "Creating account…" : "Create account"}
                </button>
            </form>
        </AuthLayout>
    );
}
