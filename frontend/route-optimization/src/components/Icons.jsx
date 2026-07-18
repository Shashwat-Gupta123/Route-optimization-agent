/**
 * Minimal outline-style SVG icons (line icons, consistent with MAQ site style).
 * Each accepts a `size` prop; stroke uses currentColor so callers control color.
 */
const base = {
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round",
    strokeLinejoin: "round",
};

export function BellIcon({ size = 20 }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
            <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
    );
}

export function RouteIcon({ size = 18 }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
            <circle cx="6" cy="19" r="2" />
            <circle cx="18" cy="5" r="2" />
            <path d="M8 19h6a4 4 0 0 0 0-8H8a4 4 0 0 1 0-8h4" />
        </svg>
    );
}

export function TruckIcon({ size = 18 }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
            <path d="M1 3h15v13H1z" />
            <path d="M16 8h4l3 3v5h-7z" />
            <circle cx="5.5" cy="18.5" r="1.5" />
            <circle cx="18.5" cy="18.5" r="1.5" />
        </svg>
    );
}

export function CloudIcon({ size = 18 }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
            <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z" />
        </svg>
    );
}

export function ChartIcon({ size = 18 }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
            <path d="M3 3v18h18" />
            <path d="M7 14l4-4 3 3 5-6" />
        </svg>
    );
}

export function PackageIcon({ size = 18 }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
            <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
            <path d="M3.27 6.96 12 12.01l8.73-5.05M12 22.08V12" />
        </svg>
    );
}

export function ClockIcon({ size = 18 }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
            <circle cx="12" cy="12" r="9" />
            <path d="M12 7v5l3 2" />
        </svg>
    );
}

export function LeafIcon({ size = 18 }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
            <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10z" />
            <path d="M2 21c0-3 1.85-5.36 5.08-6" />
        </svg>
    );
}

export function CoinIcon({ size = 18 }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
            <circle cx="12" cy="12" r="9" />
            <path d="M12 7v10M9.5 9.5h4a1.5 1.5 0 0 1 0 3h-3a1.5 1.5 0 0 0 0 3h4" />
        </svg>
    );
}

export function GaugeIcon({ size = 18 }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
            <path d="M12 14a2 2 0 1 0 0-4 2 2 0 0 0 0 4z" />
            <path d="M13.4 12.6 19 7M4 20a8 8 0 1 1 16 0" />
        </svg>
    );
}

export function UserIcon({ size = 18 }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
        </svg>
    );
}

export function LogoutIcon({ size = 18 }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <path d="M16 17l5-5-5-5M21 12H9" />
        </svg>
    );
}

export function BrandLogo({ size = 32, className = "" }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
            <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
            <line x1="8" y1="21" x2="16" y2="21"></line>
            <line x1="12" y1="17" x2="12" y2="21"></line>
            <circle cx="7" cy="10" r="1"></circle>
            <circle cx="17" cy="10" r="1"></circle>
            <path d="M7 10l5-3 5 3"></path>
        </svg>
    );
}
