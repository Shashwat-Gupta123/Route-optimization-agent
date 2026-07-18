# Route Optimizer — Component 2 & 3: Real-Time Monitoring + Analytics Dashboard
## Detailed Requirements & Build Prompts

---

## 0. Demo-mode notice (applies to both components)

You don't have real GPS/telematics hardware yet. For this phase:
- Vehicle positions are **hardcoded/simulated**, stored in `backend/db/vehicle_locations.json`,
  not pulled from a live device. Treat this file exactly like a live-tracking API response —
  the rest of the system (map, alerts, re-optimization) should not care that it's fake.
- Disruptions (traffic jam, breakdown, urgent order) are **manually triggered** from the UI
  via a "Simulate Disruption" control, instead of detected from real telematics events.
- This means swapping in real GPS later (e.g. Traccar) only requires replacing how
  `vehicle_locations.json` gets updated — the agent, endpoints, and UI don't change.

---

## 1. Component 2 — Real-Time Monitoring & Disruption Handling

### 1.1 Purpose
Once a route plan is approved (Component 1), the dispatch manager needs to see where
vehicles are, get alerted when something goes wrong (ETA miss, breakdown, urgent new
order), and trigger a re-optimization of the *remaining* stops without re-planning the
whole day from scratch.

### 1.2 Functional Requirements

**Live map (simulated positions)**
- Show each vehicle as a marker on the map at its `current_location` from
  `vehicle_locations.json`, alongside the approved route's remaining stops.
- Marker color/icon reflects `status`: on_route (green), delayed (orange),
  breakdown/maintenance (red), completed (gray).
- Hovering a vehicle marker shows: vehicle_id, driver name, current speed, next stop,
  ETA, and `eta_deviation_min`.

**Disruption simulation controls (demo-mode UI)**
- "Simulate Traffic Jam" button: applies an ETA delay to a chosen vehicle
  (`eta_deviation_min` increases) and triggers an alert if the deviation exceeds a
  threshold (e.g. 10 min — put this threshold in `config.json`).
- "Simulate Breakdown" button: marks a chosen vehicle as `status: breakdown`, flags
  its remaining assigned shipments as needing reassignment, and triggers a critical alert.
- "Add Urgent Order" button: injects a new shipment (form: store, weight, deadline)
  into the pending pool for the next re-optimization run.

**Alerting — email + dashboard**
- Every alert (ETA deviation past threshold, breakdown, urgent order added) is:
  1. Appended to `alerts.json` (so it shows in the UI's alert panel), and
  2. Sent via email to the dispatch manager's address (from `config.json`).
- The UI has a persistent **alerts panel** (bell icon + badge count of unacknowledged
  alerts) listing recent alerts with severity color, timestamp, and an "Acknowledge"
  action that marks `acknowledged: true`.
- New alerts appearing while the UI is open should surface as a toast/banner (poll
  `GET /api/alerts` every ~15s for this demo — no need for websockets yet).

**Re-optimization**
- "Re-optimize Now" button: takes the disrupted vehicle's remaining unvisited stops
  (plus any newly added urgent orders) and re-runs the VRP solver — via the same
  `optimize_routes_tool` from Component 1 — treating current vehicle positions as the
  new starting points instead of the warehouse.
- Shows a before/after comparison: old remaining route vs. new remaining route
  (distance, ETA, affected stores).
- On confirm, updates `route_plan_sample.json` and `shipments.json` with the revised
  assignments, and triggers a "Store notified" email/alert for each store whose ETA
  changed by more than the configured threshold.

**Notify stores of revised ETAs**
- For this demo phase, "notifying stores" means sending an email (to the store's
  `contact_person`/email in `stores.json` — add an `email` field to `stores.json` if
  missing) with the new ETA. No real store-facing push API needed yet.

### 1.3 New MAF tools (added to `backend/app/tools.py`)
- `detect_eta_deviation_tool`: compares a vehicle's current position/speed against
  its planned route to compute `eta_deviation_min`; flags if over the configured
  threshold.
- `reoptimize_remaining_tool`: wraps `optimize_routes_tool`, but takes the vehicle's
  current location as the route's start point instead of the warehouse, and only the
  stops not yet completed.
- `send_alert_tool`: writes an alert to `alerts.json` and sends the email (via
  `smtplib` using an app password, or a free transactional email API — see API keys
  below). Takes `channels: ["email", "dashboard"]` so some alerts can be
  dashboard-only if you want quieter ones later.

### 1.4 Backend endpoints
- `GET  /api/vehicle-locations` → current simulated positions + status for all vehicles
- `POST /api/simulate/traffic-jam` → body: `{ vehicle_id, delay_min }`. Updates
  `vehicle_locations.json`, calls `detect_eta_deviation_tool`, fires alert if needed.
- `POST /api/simulate/breakdown` → body: `{ vehicle_id }`. Marks vehicle down,
  flags its remaining shipments, fires a critical alert via `send_alert_tool`.
- `POST /api/simulate/urgent-order` → body: shipment fields. Adds to `shipments.json`
  with `status: pending`.
- `GET  /api/alerts` → list alerts, most recent first
- `POST /api/alerts/{alert_id}/acknowledge` → marks acknowledged
- `POST /api/reoptimize` → body: `{ vehicle_id }` (or `{ affected_vehicle_ids: [...] }`
  for multi-vehicle disruptions). Runs `reoptimize_remaining_tool`, returns
  before/after comparison. Does not persist until...
- `POST /api/reoptimize/confirm` → body: `{ plan_id }`. Persists the new plan and
  fires "store notified" alerts/emails for stores with materially changed ETAs.

### 1.5 New/updated data files
- **`backend/db/vehicle_locations.json`** *(already created — see attached)*: simulated
  per-vehicle position, speed, status, next stop, ETA, and deviation.
- **`backend/db/alerts.json`** *(already created — see attached)*: alert log with type,
  severity, message, channels, acknowledged flag.
- **`stores.json`**: add an `"email"` field per store (needed for the "notify stores"
  email step) if it isn't already there.
- **`config.json`**: add an `alerting` section:
  ```json
  "alerting": {
    "eta_deviation_threshold_min": 10,
    "dispatch_manager_email": "dispatch.gnhub01@example-warehouse.com",
    "smtp_host_env_var": "SMTP_HOST",
    "smtp_user_env_var": "SMTP_USER",
    "smtp_password_env_var": "SMTP_PASSWORD",
    "email_from_env_var": "ALERT_EMAIL_FROM"
  }
  ```

### 1.6 Build prompt — Component 2 backend (run against `backend/app/`)

```
Extend the existing FastAPI + Microsoft Agent Framework backend with real-time
monitoring and disruption handling, in demo mode (simulated GPS, not live
telematics). Requirements:

1. Read vehicle positions from backend/db/vehicle_locations.json — treat this file
   exactly like a live GPS feed response; do not assume it's static, since demo
   endpoints will mutate it.

2. Add three MAF tools to backend/app/tools.py:
   - detect_eta_deviation_tool: given a vehicle's current_location, current_speed,
     and its planned route stops, estimate revised ETA to the next stop and compute
     eta_deviation_min versus the originally planned ETA. Flag deviation as an alert
     if it exceeds config.json's alerting.eta_deviation_threshold_min.
   - reoptimize_remaining_tool: wraps the existing optimize_routes_tool from
     Component 1, but the route's starting point is the vehicle's current_location
     (not the warehouse), and only unvisited stops are included as demand. Returns a
     revised route in the same RoutePlan shape as Component 1.
   - send_alert_tool: appends an alert object to backend/db/alerts.json (schema:
     alert_id, type, severity, vehicle_id, shipment_id, message, created_at,
     channel, acknowledged) and, if "email" is in the channel list, sends an email
     using smtplib with credentials read from the env vars named in config.json's
     alerting section (SMTP_HOST, SMTP_USER, SMTP_PASSWORD, ALERT_EMAIL_FROM, all
     loaded from backend/.env — never hardcode credentials).

3. Expose these endpoints, all under backend/app/main.py (register a new router,
   e.g. monitoring_router, to keep this separate from Component 1's routes):
   - GET  /api/vehicle-locations
   - POST /api/simulate/traffic-jam        body: { vehicle_id, delay_min }
   - POST /api/simulate/breakdown          body: { vehicle_id }
   - POST /api/simulate/urgent-order       body: shipment fields, writes to
                                             shipments.json with status "pending"
   - GET  /api/alerts
   - POST /api/alerts/{alert_id}/acknowledge
   - POST /api/reoptimize                  body: { vehicle_id } or
                                             { affected_vehicle_ids }, calls
                                             reoptimize_remaining_tool, returns a
                                             before/after comparison, does NOT persist
   - POST /api/reoptimize/confirm          body: { plan_id }, persists the revised
                                             plan into route_plan_sample.json and
                                             shipments.json, then calls
                                             send_alert_tool once per store whose ETA
                                             changed by more than the configured
                                             threshold, with a message like "Revised
                                             ETA for <store_name>: <new_eta>"

4. Every simulate/* endpoint and /api/reoptimize/confirm should call send_alert_tool
   with channel: ["email", "dashboard"] for breakdowns and threshold-exceeding
   deviations; urgent orders can be dashboard-only unless you want them emailed too.

5. Add the "email" field to backend/db/stores.json if missing (needed for store
   notification emails) — use a placeholder pattern like
   "storename.storeid@example-warehouse.com" for demo data, don't invent real emails.

6. Add an "alerting" section to backend/db/config.json per the schema shown in the
   requirements doc, and add SMTP_HOST/SMTP_USER/SMTP_PASSWORD/ALERT_EMAIL_FROM to
   backend/.env (values can be a free Gmail app-password setup, or a free tier
   transactional email API like Brevo — either way, keep this pluggable via env vars).

7. Use only free/open-source approaches: Python's built-in smtplib (no paid email
   API required) is sufficient; no new paid dependency needed for email sending.
```

### 1.7 Build prompt — Component 2 frontend (run against `frontend/route-optimization/`)

```
Add a real-time monitoring view to this React + Vite app, alongside the existing
Route Planner screen. Backend endpoints (see Component 2 backend spec) are all
under http://localhost:8000/api/. Requirements:

1. New page/component: LiveMonitoring.jsx (or .tsx), reachable via a nav link/tab
   next to the Route Planner screen.

2. Map section (reuse the react-leaflet setup from Component 1):
   - Poll GET /api/vehicle-locations every ~10 seconds and update vehicle markers.
   - Marker color by status: on_route = green, delayed (eta_deviation_min > 0) =
     orange, breakdown/maintenance = red, completed = gray.
   - Hovering a vehicle marker shows a tooltip: vehicle_id, driver, speed, next
     stop, ETA, deviation.
   - Show the approved route's remaining stops as markers too, distinguishing
     completed vs upcoming stops (e.g. filled vs outlined icons).

3. Simulation control panel (small form, clearly labeled "Demo Controls — Simulate
   Disruption" so it reads as a demo affordance, not a production feature):
   - "Simulate Traffic Jam": select a vehicle, enter delay minutes, calls
     POST /api/simulate/traffic-jam
   - "Simulate Breakdown": select a vehicle, calls POST /api/simulate/breakdown
   - "Add Urgent Order": small form (store, weight, deadline), calls
     POST /api/simulate/urgent-order

4. Alerts panel: a bell icon in the header with an unread-count badge. Clicking it
   opens a panel listing alerts from GET /api/alerts (poll every ~15s), newest
   first, color-coded by severity, each with an "Acknowledge" button calling
   POST /api/alerts/{alert_id}/acknowledge. Show a toast/banner when a new
   unacknowledged alert appears since the last poll.

5. Re-optimize flow: when a vehicle has an active alert (deviation or breakdown), show
   a "Re-optimize Now" button next to that vehicle. Clicking it calls
   POST /api/reoptimize, then shows a before/after comparison (old vs new remaining
   route — reuse the map + a small comparison table from Component 1's patterns).
   A "Confirm" button calls POST /api/reoptimize/confirm.

6. Match existing project conventions (component structure, styling, linting) from
   the Component 1 build. Functional components + hooks only.
```

---

## 2. Component 3 — Analytics Dashboard

### 2.1 Purpose
The logistics manager wants a weekly/monthly view of how routing is actually
performing — not just today's plan — so they can see cost savings, delivery
reliability, and where things go wrong (e.g. weather-driven delays).

### 2.2 Functional Requirements

**KPI summary cards (top of dashboard)**
Computed from `route_history.json` + today's data, for a selected date range:
- Total shipments delivered
- On-time delivery % (average `on_time_pct`)
- Total distance traveled (planned vs actual)
- Total fuel cost (planned vs actual)
- Total CO2 emissions
- Average cost per delivery
- Average vehicle utilization %
- Average estimated vs actual delivery time (ETA accuracy) — this is the one that
  should be computed via the same OR-Tools-based estimation logic as Component 1
  (`optimize_routes_tool`'s duration output), compared against the actual recorded
  duration, not just re-stated from history.

**Trend charts**
- Distance/cost/duration: planned vs actual, over the selected date range (line chart)
- On-time % over time (line chart)
- Vehicle utilization % over time (bar chart)

**Cost breakdown**
- Fuel cost vs. labour cost vs. vehicle wear, as a share of total delivery cost
  (pie or stacked bar). Labour cost = driver shift hours × a configurable hourly
  rate; vehicle wear = a configurable per-km depreciation rate — both go in
  `config.json` as new fields since they're not in the current schema.

**Weather correlation**
- Simple view: average delay (actual − planned duration) grouped by
  `weather_condition` from `route_history.json`, so the manager can see e.g. "rain
  days average +23% duration."

**Alerts (digest, not real-time)**
- A "Send Weekly Report" button that emails a summary of the above KPIs (for the
  selected range) to the dispatch manager, and also posts a digest entry to
  `alerts.json` (type: `weekly_report`, dashboard-only) so it shows up in the same
  alerts panel built in Component 2.

### 2.3 New MAF tool
- `compute_kpi_tool`: takes a date range, reads `route_history.json` (+ today's
  `route_plan_sample.json` if in range), and returns the aggregated KPI object below.
  For the "estimated vs actual delivery time" KPI specifically, it re-derives the
  estimate by calling `optimize_routes_tool` with that day's historical
  shipments/fleet inputs (if available) rather than trusting a pre-stored planned
  number — this is the "must use OR-Tools" requirement for this component.

### 2.4 Backend endpoints
- `GET /api/kpis/summary?from=YYYY-MM-DD&to=YYYY-MM-DD` → aggregated KPI card data
- `GET /api/kpis/trends?from=...&to=...` → time series for the trend charts
- `GET /api/kpis/cost-breakdown?from=...&to=...` → fuel/labour/wear split
- `GET /api/kpis/weather-correlation` → average delay grouped by weather_condition
- `POST /api/kpis/send-report` → body: `{ from, to }`. Emails the summary + posts a
  dashboard alert via `send_alert_tool` (reused from Component 2).

### 2.5 New/updated data files
- **`backend/db/route_history.json`** *(already created — see attached)*: ~10 days
  of planned-vs-actual daily route performance, including `weather_condition`, for
  trend charts and weather correlation.
- **`config.json`**: add a `cost_model` section:
  ```json
  "cost_model": {
    "labour_cost_per_hour_inr": 120,
    "vehicle_wear_cost_per_km_inr": 2.5
  }
  ```

### 2.6 Build prompt — Component 3 backend (run against `backend/app/`)

```
Extend the existing FastAPI + Microsoft Agent Framework backend with an analytics
KPI layer. Requirements:

1. Add compute_kpi_tool to backend/app/tools.py: takes a date range (from, to),
   reads backend/db/route_history.json for historical days in range, and today's
   backend/db/route_plan_sample.json if its date falls in range. Returns:
   - totals: shipments_delivered, on_time_pct (avg), total_distance_planned_km,
     total_distance_actual_km, total_fuel_cost_planned_inr,
     total_fuel_cost_actual_inr, total_co2_emissions_kg,
     avg_cost_per_delivery_inr, avg_vehicle_utilization_pct
   - eta_accuracy: for the "estimated vs actual delivery time" KPI, re-run
     optimize_routes_tool (from Component 1) against each historical day's
     shipments/fleet snapshot if available, to produce a freshly computed estimate,
     then compare it to that day's recorded actual duration — return both the
     recomputed estimate and the actual, plus the delta. If no shipment/fleet
     snapshot exists for a historical day (only aggregate totals are stored), fall
     back to the stored total_duration_planned_min instead of failing.
   - cost_breakdown: fuel_cost_inr (from route_history), labour_cost_inr (sum of
     driver shift hours in range × config.json's cost_model.labour_cost_per_hour_inr),
     vehicle_wear_cost_inr (total_distance_actual_km × config.json's
     cost_model.vehicle_wear_cost_per_km_inr)
   - weather_correlation: group route_history.json entries by weather_condition,
     return avg (actual_duration - planned_duration) per condition

2. Expose endpoints under a new analytics_router in backend/app/main.py:
   - GET  /api/kpis/summary?from=...&to=...
   - GET  /api/kpis/trends?from=...&to=...        (daily time series for charts)
   - GET  /api/kpis/cost-breakdown?from=...&to=...
   - GET  /api/kpis/weather-correlation
   - POST /api/kpis/send-report   body: { from, to }. Formats the summary as a
     readable email body, sends it via the same send_alert_tool mechanism built in
     Component 2 (email + dashboard channel, alert type "weekly_report").

3. Add a "cost_model" section to backend/db/config.json per the schema in the
   requirements doc.

4. Validate date ranges and return a clear 400 error if from > to or the range has
   no data, rather than returning empty/misleading KPIs silently.
```

### 2.7 Build prompt — Component 3 frontend (run against `frontend/route-optimization/`)

```
Add an Analytics Dashboard page to this React + Vite app, alongside Route Planner
and Live Monitoring. Requirements:

1. New page: AnalyticsDashboard.jsx (or .tsx), reachable via a nav link/tab.

2. Add a charting library (recharts is a good free/OSS fit for React) as a new
   dependency if one isn't already present in package.json.

3. Date range picker at the top (defaults to last 14 days), driving all queries
   below.

4. KPI summary cards row: total shipments, on-time %, total distance (planned vs
   actual), total fuel cost (planned vs actual), total CO2 emissions, avg cost per
   delivery, avg vehicle utilization %, and an "ETA accuracy" card showing the
   recomputed estimate vs actual delivery time delta — from GET /api/kpis/summary.

5. Trend charts section: line chart for distance/duration/cost (planned vs actual)
   over the date range, line chart for on-time % over time, bar chart for vehicle
   utilization % over time — from GET /api/kpis/trends.

6. Cost breakdown chart: pie or stacked bar showing fuel vs labour vs vehicle wear
   share of total cost — from GET /api/kpis/cost-breakdown.

7. Weather correlation panel: simple bar chart or table showing average delay by
   weather condition — from GET /api/kpis/weather-correlation.

8. "Send Weekly Report" button: calls POST /api/kpis/send-report with the current
   date range, shows a success toast on completion ("Report sent to dispatch
   manager").

9. Match existing project conventions (component structure, styling, linting) from
   the Component 1/2 builds. Functional components + hooks only.
```

---

## 3. Free API keys / setup needed for Components 2 & 3

| # | What | Free option | Key required? |
|---|---|---|---|
| 1 | Sending alert emails | **Gmail SMTP with an App Password** (free, uses your existing Gmail) via Python's built-in `smtplib` | No API key — just an app password stored as `SMTP_PASSWORD` in `.env` |
| 2 | Alternative email option | **Brevo** (formerly Sendinblue) free tier — 300 emails/day free | Yes, free signup: https://www.brevo.com |
| 3 | Alternative email option | **Resend** free tier — 100 emails/day free, developer-friendly API | Yes, free signup: https://resend.com |

**Recommendation**: start with Gmail SMTP + an app password — zero new signups, works
immediately with `smtplib`, and is enough for a demo dispatch-manager inbox. Move to
Brevo/Resend later if you need higher volume or nicer deliverability.

No new keys are needed for anything else in Components 2 or 3 — vehicle locations,
alerts, and historical KPI data all come from the local JSON files in `backend/db/`.
