# Route Optimizer — Frontend Application
## Detailed Requirements & Build Prompt (React + Vite, all 3 components)

---

## 1. Purpose of this document

Components 1, 2, and 3 each had their own frontend build prompt scoped to a single
page. This document ties them into **one coherent application shell** — navigation,
shared layout, shared API client, environment config, and design direction — so the
three pages feel like one product instead of three separate demos bolted together.

Use this prompt **first** (or alongside Component 1's backend prompt) to scaffold the
app shell, then layer in each component's page-specific prompt from the earlier
documents.

---

## 2. Application Structure

### 2.1 Pages
| Route | Page | Source doc |
|---|---|---|
| `/` or `/planner` | Route Planner | Component 1 |
| `/monitoring` | Live Monitoring | Component 2 |
| `/analytics` | Analytics Dashboard | Component 3 |

### 2.2 Shared shell
- **Top navigation bar**: app name/logo, links to the 3 pages (highlight active
  route), and a persistent **alerts bell** (icon + unread-count badge) on the right —
  shared across all pages since alerts from Component 2/3 are relevant everywhere,
  not just on the Monitoring page.
- **Alerts panel**: a slide-over/dropdown triggered by the bell, showing recent
  alerts from `GET /api/alerts`, reusable on every page (build it once in the shell,
  not duplicated per page).
- **Layout**: sidebar-free, top-nav + full-width content area works well here since
  each page (map + table, map + controls, charts) needs horizontal room. A left
  sidebar is fine too if that matches the existing project's conventions — check
  `src/` first.

### 2.3 Shared API client
- One Axios (or fetch-wrapper) instance configured with `baseURL` from
  `VITE_API_BASE_URL`, used by every page — don't let each page construct its own
  URLs or duplicate error-handling logic.
- Centralize the 422 "infeasible" and 400 "bad date range" error handling here (e.g.
  an interceptor that normalizes backend errors into a consistent shape components
  can render), so every page shows errors the same way instead of each reinventing it.

### 2.4 Design direction — MAQ Software brand, executive dashboard

This tool should look like something you'd present in an internal leadership review —
polished, data-forward, and on-brand with MAQ Software's own site — not a generic
open-source admin template. Match the visual language of maqsoftware.com: clean white
canvas, a single confident red as the only accent color, dark charcoal text, generous
whitespace, minimal borders, and understated icon-led cards. KPIs and charts are the
centerpiece — they should read clearly at a glance, the way an executive skimming a
dashboard for 10 seconds would need.

**Color tokens** (extract the exact red from the MAQ logo — approximate values below,
adjust to match precisely):
```css
--color-primary: #D6001C;        /* MAQ red — logo, active nav, primary CTA, primary
                                     chart series, KPI accent */
--color-primary-hover: #B10017;   /* darker red for hover/active states */
--color-text: #1A1A1A;            /* near-black body/heading text, not pure black */
--color-text-muted: #6B6B6B;      /* secondary text, labels, captions */
--color-bg: #FFFFFF;              /* primary canvas */
--color-bg-subtle: #FAFAFA;       /* section backgrounds, alternating rows */
--color-border: #E5E5E5;          /* card borders, dividers — always subtle, never heavy */
--color-success: #1E8E3E;         /* on-time / healthy status — used sparingly, not as
                                     a second brand color */
--color-warning: #D97706;         /* delayed / ETA deviation */
--color-critical: #D6001C;        /* breakdown / critical alerts — reuses brand red,
                                     don't introduce a separate alert red */
```

**Typography**
- Clean sans-serif (system font stack, or Inter if the project wants a webfont) —
  matches MAQ's site typography.
- Section headings: bold, large, dark charcoal (e.g. "Services we provide" style on
  maqsoftware.com) — e.g. `font-weight: 700`, `font-size: 1.5–1.75rem`.
- KPI numbers: the largest, boldest text on any page — these are the first thing an
  executive should see. Body/table text stays regular weight and smaller.

**Component style**
- Cards (KPI cards, service-style summary cards): white background, `1px solid
  var(--color-border)`, rounded corners (`8px`), generous internal padding
  (`24–32px`), no heavy drop shadows — at most a very subtle shadow on hover, mirroring
  the flat, minimal card style used for "Services we provide" on the MAQ site.
- Icons: simple outline/line-style icons (not filled, not illustrative) — consistent
  with the minimalist icons used for each service card on maqsoftware.com.
- Buttons: primary actions use solid `var(--color-primary)` background with white
  text; secondary actions use an outlined/ghost style with dark text — avoid
  multiple competing button colors.
- Navigation: white top bar, dark text links, active route underlined or colored in
  `var(--color-primary)` — mirrors the MAQ site's top nav treatment.

**Charts (Analytics Dashboard especially)**
- Use `var(--color-primary)` (red) as the primary/first data series in every chart —
  it should be immediately recognizable as "the MAQ number."
- Secondary series and comparison lines (e.g. "actual" vs "planned") use neutral
  grays, not a second bright color — reserve color for what matters most.
- Status-based charts (on-time %, alerts by severity) use the success/warning/critical
  tokens above, not an arbitrary chart-library default palette.
- Keep chart chrome minimal: light gridlines (`var(--color-border)`), no heavy
  backgrounds, clear axis labels, and a legend only when more than one series is shown.

**Route plan colors (Route Planner map)**
- Component 1 specifies distinct colors per plan (fastest/cheapest/balanced). Keep
  these outside the red/status palette so they're never confused with brand or
  critical-alert red — use blue, green/teal, and amber for the three plans, and
  reserve `var(--color-primary)` red strictly for brand elements (nav, buttons,
  primary KPI/chart series) and critical status.

**What to avoid**
- No gradient backgrounds, no illustration-heavy empty states, no playful/rounded
  "consumer app" styling — this is an executive-facing operations tool.
- Don't introduce a second accent color "for variety" — every additional color should
  carry meaning (status), not decoration.
- Don't screenshot or copy any of MAQ Software's actual marketing copy, KPI figures,
  or page content — only the color palette, typography feel, and card/nav styling
  patterns should carry over. All KPI values and copy in this app come from your own
  route/shipment data.

---

## 3. Folder Structure

```
frontend/route-optimization/src/
├── api/
│   └── client.js              # shared Axios instance + error normalization
├── layout/
│   ├── AppShell.jsx            # top nav + alerts bell + content outlet
│   └── AlertsPanel.jsx         # shared slide-over, used by AppShell
├── pages/
│   ├── RoutePlanner.jsx        # Component 1
│   ├── LiveMonitoring.jsx      # Component 2
│   └── AnalyticsDashboard.jsx  # Component 3
├── components/
│   ├── route-planner/
│   │   ├── ShipmentSidebar.jsx
│   │   ├── RouteMap.jsx
│   │   └── PlanComparisonTable.jsx
│   ├── monitoring/
│   │   ├── VehicleMap.jsx
│   │   ├── DisruptionControls.jsx
│   │   └── ReoptimizeComparison.jsx
│   └── analytics/
│       ├── KpiCards.jsx
│       ├── TrendCharts.jsx
│       ├── CostBreakdownChart.jsx
│       └── WeatherCorrelationPanel.jsx
├── hooks/
│   ├── useAlerts.js             # polling hook shared by AppShell + monitoring page
│   └── usePolling.js            # generic interval-polling hook, reused wherever needed
├── App.jsx                      # react-router setup
└── .env                         # VITE_API_BASE_URL=http://localhost:8000
```

---

## 4. Dependencies to add (all free/open-source)

| Package | Purpose |
|---|---|
| `react-router-dom` | Routing between the 3 pages |
| `axios` | API client (skip if the project already uses fetch consistently) |
| `react-leaflet` + `leaflet` | Maps (Route Planner + Live Monitoring) |
| `recharts` | Charts (Analytics Dashboard) |

Check `package.json` first — only add what's missing.

---

## 5. Master Build Prompt (paste into Claude Code, run before/alongside page-specific prompts)

```
Scaffold the application shell for this existing React + Vite project
(frontend/route-optimization/), which will host three pages: Route Planner, Live
Monitoring, and Analytics Dashboard. The backend is a FastAPI server (assume
http://localhost:8000) — see the Component 1/2/3 backend specs for its exact
endpoints. Requirements:

1. Add react-router-dom (if not already present) and set up routes in App.jsx:
   "/" or "/planner" → RoutePlanner, "/monitoring" → LiveMonitoring,
   "/analytics" → AnalyticsDashboard.

2. Build layout/AppShell.jsx: a top navigation bar with links to the three pages
   (highlighting the active route), and an alerts bell icon on the right showing an
   unread-count badge. Wrap all page routes in this shell so the nav and bell are
   always visible. Use React Router's <Outlet /> pattern (or equivalent) so pages
   render inside the shell.

3. Build layout/AlertsPanel.jsx: a slide-over or dropdown panel, triggered by the
   bell in AppShell, listing alerts from GET /api/alerts (poll every ~15s via a
   shared hooks/useAlerts.js hook), color-coded by severity, each with an
   "Acknowledge" button calling POST /api/alerts/{alert_id}/acknowledge. This panel
   must be usable from any page, not just the Live Monitoring page — build it once
   in the shell.

4. Build hooks/usePolling.js: a small generic hook that takes a fetch function and
   an interval, and returns the latest data — reuse this for alerts polling in
   Component 2/3's polling needs (vehicle locations, alerts) instead of writing
   separate setInterval logic in each component.

5. Build api/client.js: a single Axios instance with baseURL from
   import.meta.env.VITE_API_BASE_URL, plus a response interceptor that normalizes
   backend error responses (422 "infeasible", 400 "bad date range", etc.) into a
   consistent { message, status } shape that any page/component can render in an
   error state without re-implementing parsing logic.

6. Create/update frontend/route-optimization/.env with
   VITE_API_BASE_URL=http://localhost:8000 — never hardcode this URL inside
   components; always import from the env var via api/client.js.

7. Set up empty placeholder pages/RoutePlanner.jsx, pages/LiveMonitoring.jsx, and
   pages/AnalyticsDashboard.jsx (just a heading each for now) wired into the router,
   so the shell + navigation can be verified working before the page-specific
   prompts (Component 1/2/3) fill in their actual content.

8. Follow the existing project's conventions: check package.json for the styling
   approach already in use (Tailwind, CSS modules, styled-components, plain CSS)
   and .oxlintrc.json for lint rules — use whatever's already there rather than
   introducing a second styling system. Functional components + hooks only, no
   class components.

9. Design direction: build this as a polished, executive-facing operations tool in
   MAQ Software's brand style — white canvas, a single confident red accent
   (--color-primary), dark charcoal text, minimal borders, and understated
   outline-style icons, matching the visual language of maqsoftware.com (clean top
   nav, flat bordered cards, bold section headings). Set up the color tokens as CSS
   custom properties (or Tailwind theme extension, matching whatever the project
   already uses) exactly as specified in section 2.4 of this document, so every
   page/component pulls from the same palette instead of hardcoding colors. Reserve
   red strictly for brand elements and critical status — route plan polylines and
   general chart series should use blue/green/amber, not red, to avoid clashing
   with alert/critical meaning. KPI numbers should be the largest, boldest text on
   any page.

After this shell is scaffolded and verified (all three nav links work, alerts bell
opens an empty/working panel), run the Component 1 frontend prompt to fill in
RoutePlanner.jsx, then Component 2's for LiveMonitoring.jsx, then Component 3's for
AnalyticsDashboard.jsx — each of those prompts assumes this shell, hooks, and
api/client.js already exist and should import/reuse them rather than duplicating
API-calling or polling logic.
```

---

## 6. Suggested build order for the full frontend

1. **This prompt** — app shell, routing, alerts panel, shared API client, empty pages
2. Verify: nav works, alerts bell opens (even with no real alerts yet since backend
   Component 2 may not be built yet — mock the endpoint response if needed)
3. **Component 1 frontend prompt** — fills in Route Planner page
4. **Component 2 frontend prompt** — fills in Live Monitoring page (now the alerts
   panel in the shell will show real data too, since Component 2's backend exists)
5. **Component 3 frontend prompt** — fills in Analytics Dashboard page