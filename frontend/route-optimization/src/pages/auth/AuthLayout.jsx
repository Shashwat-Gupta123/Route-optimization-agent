import { BrandLogo } from "../../components/Icons";

/**
 * Shared branded shell for the Login / Signup pages. Left panel carries the MAQ
 * brand + value props; right panel hosts the form card passed as children. Keeps
 * both auth pages visually consistent and avoids duplicating layout markup.
 */
export default function AuthLayout({ title, subtitle, children, footer }) {
    return (
        <div className="auth-shell">
            <aside className="auth-brand-panel">
                <div className="auth-brand-top">
                    <BrandLogo className="auth-brand-logo" size={48} color="white" />
                </div>
                <div className="auth-brand-copy">
                    <h1>Route Optimizer</h1>
                    <p>
                        Plan, monitor and analyze warehouse deliveries from a
                        single executive operations console.
                    </p>
                    <ul className="auth-brand-points">
                        <li>Optimized multi-vehicle route planning</li>
                        <li>Real-time disruption monitoring &amp; alerts</li>
                        <li>Performance &amp; cost analytics</li>
                    </ul>
                </div>
                <div className="auth-brand-footer">
                    Route-optimization-agent · Dispatch Operations
                </div>
            </aside>

            <main className="auth-form-panel">
                <div className="auth-card">
                    <div className="auth-card-header">
                        <BrandLogo className="auth-card-logo" size={32} color="var(--color-primary)" />
                        <h2>{title}</h2>
                        {subtitle && <p className="text-muted">{subtitle}</p>}
                    </div>
                    {children}
                    {footer && <div className="auth-card-footer">{footer}</div>}
                </div>
            </main>
        </div>
    );
}
