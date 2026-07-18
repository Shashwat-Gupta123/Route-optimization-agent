import {
    createContext,
    useContext,
    useState,
    useEffect,
    useCallback,
} from "react";

/**
 * Client-side authentication provider.
 *
 * Architectural note: the FastAPI backend does not (yet) expose auth endpoints,
 * so this implements a self-contained, demo-grade auth layer entirely on the
 * client. Registered users are persisted in localStorage and passwords are
 * stored only as SHA-256 hashes (never plaintext). The active session is kept
 * in localStorage so a refresh keeps the user signed in. When a real
 * /api/auth backend is added later, only this file needs to change — pages and
 * route guards consume it through the useAuth() hook and stay untouched.
 */

const AuthContext = createContext(null);

const USERS_KEY = "maq.ro.users";
const SESSION_KEY = "maq.ro.session";

function readUsers() {
    try {
        return JSON.parse(localStorage.getItem(USERS_KEY)) || [];
    } catch {
        return [];
    }
}

function writeUsers(users) {
    localStorage.setItem(USERS_KEY, JSON.stringify(users));
}

async function hashPassword(password) {
    const data = new TextEncoder().encode(password);
    const digest = await crypto.subtle.digest("SHA-256", data);
    return Array.from(new Uint8Array(digest))
        .map((b) => b.toString(16).padStart(2, "0"))
        .join("");
}

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [initializing, setInitializing] = useState(true);

    // Restore any persisted session on first load.
    useEffect(() => {
        try {
            const session = JSON.parse(localStorage.getItem(SESSION_KEY));
            if (session?.email) {
                setUser(session);
            }
        } catch {
            /* ignore malformed session */
        }
        setInitializing(false);
    }, []);

    const persistSession = useCallback((session) => {
        localStorage.setItem(SESSION_KEY, JSON.stringify(session));
        setUser(session);
    }, []);

    const signup = useCallback(
        async ({ name, email, password }) => {
            const normalizedEmail = email.trim().toLowerCase();
            const users = readUsers();
            if (users.some((u) => u.email === normalizedEmail)) {
                throw new Error("An account with this email already exists.");
            }
            const passwordHash = await hashPassword(password);
            const record = {
                name: name.trim(),
                email: normalizedEmail,
                passwordHash,
                createdAt: new Date().toISOString(),
            };
            writeUsers([...users, record]);
            persistSession({ name: record.name, email: record.email });
            return record;
        },
        [persistSession],
    );

    const login = useCallback(
        async ({ email, password }) => {
            const normalizedEmail = email.trim().toLowerCase();
            const users = readUsers();
            const record = users.find((u) => u.email === normalizedEmail);
            if (!record) {
                throw new Error("No account found for this email.");
            }
            const passwordHash = await hashPassword(password);
            if (passwordHash !== record.passwordHash) {
                throw new Error("Incorrect email or password.");
            }
            persistSession({ name: record.name, email: record.email });
            return record;
        },
        [persistSession],
    );

    const logout = useCallback(() => {
        localStorage.removeItem(SESSION_KEY);
        setUser(null);
    }, []);

    return (
        <AuthContext.Provider
            value={{
                user,
                isAuthenticated: !!user,
                initializing,
                signup,
                login,
                logout,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx) {
        throw new Error("useAuth must be used within an AuthProvider");
    }
    return ctx;
}
