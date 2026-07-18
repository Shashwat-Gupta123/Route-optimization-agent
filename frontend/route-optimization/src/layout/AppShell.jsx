import { useState, useRef, useEffect } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { BellIcon, UserIcon, LogoutIcon } from "../components/Icons";
import { useAlertsContext } from "../components/AlertsProvider";
import { useAuth } from "../context/AuthContext";
import AlertsPanel from "./AlertsPanel";
import ChatLauncher from "../components/chat/ChatLauncher";
import { BrandLogo } from "../components/Icons";

/**
 * Application shell: MAQ-styled top navigation bar with the brand logo, the three
 * page links, a persistent alerts bell (unread badge) and a user menu with sign
 * out. Page content renders in the <Outlet />, and the shared AlertsPanel
 * slide-over is mounted once here.
 */
export default function AppShell() {
    const [panelOpen, setPanelOpen] = useState(false);
    const [menuOpen, setMenuOpen] = useState(false);
    const menuRef = useRef(null);
    const { unacknowledgedCount } = useAlertsContext();
    const { user, logout } = useAuth();

    // Close the user menu when clicking outside it.
    useEffect(() => {
        if (!menuOpen) return undefined;
        const onClick = (e) => {
            if (menuRef.current && !menuRef.current.contains(e.target)) {
                setMenuOpen(false);
            }
        };
        document.addEventListener("mousedown", onClick);
        return () => document.removeEventListener("mousedown", onClick);
    }, [menuOpen]);

    const initials = (user?.name || user?.email || "?")
        .split(/[\s@.]+/)
        .filter(Boolean)
        .slice(0, 2)
        .map((s) => s[0].toUpperCase())
        .join("");

    return (
        <div className="app-shell">
            <header className="topnav">
                <div className="topnav-brand">
                    <BrandLogo className="topnav-logo" size={32} color="var(--color-primary)" />
                    <span className="brand-divider" />
                    <span className="brand-title">Route Optimizer</span>
                    <span className="brand-sub">Dispatch Operations</span>
                </div>

                <nav className="topnav-links">
                    <NavLink to="/planner">Route Planner</NavLink>
                    <NavLink to="/monitoring">Live Monitoring</NavLink>
                    <NavLink to="/analytics">Analytics</NavLink>
                </nav>

                <div className="topnav-actions">
                    <button
                        className="bell-btn"
                        onClick={() => setPanelOpen((o) => !o)}
                        aria-label="Alerts"
                    >
                        <BellIcon />
                        {unacknowledgedCount > 0 && (
                            <span className="bell-badge">
                                {unacknowledgedCount}
                            </span>
                        )}
                    </button>

                    <div className="user-menu" ref={menuRef}>
                        <button
                            className="user-menu-trigger"
                            onClick={() => setMenuOpen((o) => !o)}
                            aria-haspopup="menu"
                            aria-expanded={menuOpen}
                        >
                            <span className="user-avatar">{initials}</span>
                            <span className="user-name">
                                {user?.name || user?.email}
                            </span>
                        </button>
                        {menuOpen && (
                            <div className="user-dropdown" role="menu">
                                <div className="user-dropdown-header">
                                    <UserIcon size={16} />
                                    <div>
                                        <div className="user-dropdown-name">
                                            {user?.name || "Signed in"}
                                        </div>
                                        <div className="user-dropdown-email">
                                            {user?.email}
                                        </div>
                                    </div>
                                </div>
                                <button
                                    className="user-dropdown-item"
                                    onClick={logout}
                                    role="menuitem"
                                >
                                    <LogoutIcon size={16} /> Sign out
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            </header>

            <Outlet />

            <AlertsPanel open={panelOpen} onClose={() => setPanelOpen(false)} />
            <ChatLauncher />
        </div>
    );
}
