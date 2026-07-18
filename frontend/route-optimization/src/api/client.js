import axios from "axios";

/**
 * Shared Axios instance for the whole app. Base URL comes from the Vite env var
 * VITE_API_BASE_URL so the backend origin is never hardcoded in components.
 */
const client = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
    headers: { "Content-Type": "application/json" },
});

/**
 * Normalize every backend error into a consistent { message, status } shape so
 * pages/components can render errors the same way without re-parsing responses.
 * Covers FastAPI's 422 "infeasible", 400 "bad date range", and network errors.
 */
client.interceptors.response.use(
    (response) => response,
    (error) => {
        const status = error.response?.status ?? 0;
        const detail = error.response?.data?.detail;

        let message;
        if (Array.isArray(detail)) {
            // FastAPI validation errors come back as a list of {loc, msg, ...}.
            message = detail.map((d) => d.msg).join("; ");
        } else if (typeof detail === "string") {
            message = detail;
        } else if (status === 0) {
            message = "Cannot reach the backend. Is the API server running?";
        } else {
            message = error.message || "Something went wrong.";
        }

        return Promise.reject({ message, status });
    },
);

export default client;
