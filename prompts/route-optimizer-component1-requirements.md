# Route Optimizer — Component 1: Route Planner UI
## Detailed Requirements & Build Prompt

---

## 1. Project Context

**Product**: Internal agentic tool for a warehouse that ships products to multiple retail
stores daily.

**Primary user**: Warehouse dispatch/logistics manager (non-technical, works daily with
shipment lists and delivery schedules).

**Core job to be done**: Every morning, the manager has a list of stores that need shipments.
They currently plan routes manually or with basic tools. This agent should:
1. Take today's shipment list (store, quantity/weight, delivery deadline)
2. Take available fleet (vehicles, capacity)
3. Compute multiple route options (fastest / cheapest / most balanced)
4. Show the manager a map + comparison table of route options with real metrics
   (distance, ETA, fuel cost, emissions)
5. Let the manager approve one route plan

This document covers **Component 1 only**: the Route Planner UI — the interactive
planning screen where routes are generated and compared. It does not cover live
tracking, disruption re-optimization, or analytics (those are later components).

---

## 2. Functional Requirements

### 2.1 Shipment Input
- Load today's shipments from a CSV or simple form: store name, address (or lat/lon),
  quantity/weight, delivery time window (earliest/latest).
- Load warehouse (depot) location: address or lat/lon.
- Load fleet data: number of vehicles, capacity per vehicle (weight/volume units).

### 2.2 Route Computation
- Geocode store addresses to lat/lon (if not already provided).
- Build a distance/duration matrix between warehouse and all stores.
- Fetch current weather conditions relevant to the delivery zone(s).
- Run the OR-Tools VRP solver to generate **at least 3 alternative route plans**:
  - **Fastest**: minimizes total time
  - **Cheapest**: minimizes total distance/fuel cost
  - **Balanced**: weighted combination of time, cost, and emissions
- For each plan, compute: total distance (km), total duration (min), per-stop ETA,
  fuel cost estimate, CO2 emissions estimate, and an overall "effectiveness score."

### 2.3 UI — Route Planner Screen (React frontend, calling FastAPI backend)
- **Sidebar panel**: today's shipment list, fleet summary, weather/traffic alerts.
- **Map panel**: interactive map (Leaflet via react-leaflet) showing warehouse + store
  markers, with each route plan drawn as a distinct colored polyline; user can toggle
  route visibility.
- **Hover info on routes**: hovering over any segment of a route polyline shows a
  tooltip with that leg's details — from/to stop names, distance, travel time, and
  ETA at the destination stop. Hovering over a store marker shows that stop's shipment
  details (store name, weight, time window).
- **Comparison table**: one row per route plan with distance/ETA/cost/emissions/score
  columns; clicking a row highlights that route on the map.
- **Approve button**: calls the backend's approve-plan endpoint, which locks in the
  selected route plan and persists it to `backend/db/route_plan_sample.json`.
- **"Ask AI" box** (optional for v1): free-text question about the plan (e.g. "why does
  Route 2 avoid the highway?") sent to a backend endpoint that answers using an LLM
  with the route data as context.

### 2.4 Non-Functional Requirements
- Must run entirely on free/open-source tools — no paid cloud subscription required.
- Should work with a small dataset (5–20 stores, 1–5 vehicles) for a first version.
- Response time: route computation should complete within ~5–10 seconds for this scale.
- All API calls must respect free-tier rate limits (see below).

---

## 3. Tech Stack (Free / Open-Source)

| Layer | Tool | Notes |
|---|---|---|
| Optimization solver | **Google OR-Tools** | Free, Apache 2.0, no key needed |
| Routing / distance matrix | **OpenRouteService (ORS)** or **OSRM** | See API keys below |
| Geocoding (address → lat/lon) | **Nominatim (OpenStreetMap)** | Free, no key, strict rate limit |
| Weather data | **Open-Meteo** | Free, no key required at all |
| Agent orchestration | **Microsoft Agent Framework** | Open-source (MIT), matches your existing [[ead-agent]] project's stack |
| LLM reasoning (optional "Ask AI") | **Ollama** running Llama 3.1 / Mistral locally | Free, no key, runs on your machine |
| Backend API | **FastAPI** | Free, Python-native — matches `backend/app/` in your project |
| Frontend UI | **React + Vite** | Free — matches `frontend/route-optimization/` in your project |
| Map rendering | **Leaflet** via **react-leaflet** | Free, OSS — the JS equivalent of Folium for a React frontend |
| Data storage | Flat JSON files under `backend/db/` | Free, no setup needed for v1 |

---

## 4. Free API Keys You Need to Obtain

| # | Service | What it's for | Key required? | Free tier limit | Sign-up link |
|---|---|---|---|---|---|
| 1 | **OpenRouteService** | Distance/duration matrix, routing, geocoding fallback | Yes (free) | ~2,000 requests/day, 40 req/min | https://openrouteservice.org/dev/#/signup |
| 2 | **Open-Meteo** | Weather forecast for delivery zones | **No key needed** | Free for non-commercial use, generous limits | https://open-meteo.com/ (no signup) |
| 3 | **Nominatim (OSM)** | Geocoding store addresses to lat/lon | **No key needed** | 1 request/second, must set a User-Agent header | https://nominatim.org/release-docs/latest/api/Overview/ |
| 4 | **OSRM public demo** (optional, alternative to ORS) | Distance/duration matrix | **No key needed** | Public demo server, not for heavy/production use | http://project-osrm.org/ |
| 5 | **Overpass API** (optional) | Extra road network data if needed | **No key needed** | Rate-limited, fair use | https://overpass-api.de/ |

**Practical recommendation**: Start with **OpenRouteService** as your main routing/matrix
provider (needs one free signup) since it's more reliable than the public OSRM demo
server for repeated use, and pair it with **Open-Meteo** for weather (zero setup — no
key at all). This gives you a fully working v1 with just **one** API key to obtain.

---

## 5. Data Layer — `backend/db/` folder

All data lives as flat JSON files under `backend/db/`. This is the single source of
truth the app reads from (and, for `shipments.json` / `route_plan_sample.json`, writes
back to as orders get planned and approved). No database server needed for v1 —
SQLite/Postgres migration can happen later without changing the app's data access layer
if you keep a thin `data_access.py` module in front of it.

```
backend/
└── db/
    ├── config.json              # app-wide defaults, scoring weights, API key env var names
    ├── warehouse.json           # single warehouse/depot record
    ├── vehicles.json            # fleet — capacity, fuel efficiency, status, location
    ├── drivers.json             # driver roster linked to vehicles
    ├── stores.json              # delivery destinations with lat/lon, zone, receiving hours
    ├── shipments.json           # today's orders — the main planning input
    └── route_plan_sample.json   # example solver OUTPUT shape (reference/seed data)
```

### File relationships (foreign keys)
- `shipments.json[].store_id` → `stores.json[].store_id`
- `shipments.json[].warehouse_id` → `warehouse.json.warehouse_id`
- `shipments.json[].assigned_vehicle_id` / `assigned_plan_id` → filled in once a plan is approved
- `vehicles.json[].assigned_driver_id` → `drivers.json[].driver_id`
- `route_plan_sample.json.routes[].stops[].shipment_id` → `shipments.json[].shipment_id`
- `config.json.data_files` → paths to all of the above, so the app never hardcodes filenames

### Key schema (for reference — see actual JSON files for full field list)

```yaml
Shipment:
  shipment_id: str
  store_id: str
  warehouse_id: str
  items: list[{ sku, description, quantity }]
  weight_kg: float
  volume_m3: float
  earliest_delivery_time: str   # "09:00"
  latest_delivery_time: str     # "13:00"
  priority: str                 # low | normal | high
  special_handling: bool
  status: str                   # pending | assigned | delivered | cancelled
  assigned_plan_id: str | null
  assigned_vehicle_id: str | null

Vehicle:
  vehicle_id: str
  capacity_kg: float
  fuel_efficiency_km_per_l: float
  status: str                   # available | maintenance | on_route
  assigned_driver_id: str

Store:
  store_id: str
  lat: float
  lon: float
  zone: str
  priority_tier: str
  receiving_hours: { open, close }

RoutePlan (output):
  plan_id: str
  plan_name: str                # fastest | cheapest | balanced
  routes: list[VehicleRoute]
  totals: { total_distance_km, total_duration_min, total_fuel_cost_inr,
            total_co2_emissions_kg, makespan_min, on_time_pct }
  effectiveness_score: float
  status: str                   # draft | approved
```

### `config.json` — scoring & cost defaults
Holds the effectiveness-score weights (distance/time/fuel/emissions), per-vehicle-type
CO2 emission factors, default fuel price, and the API provider/env-var names — so none
of these values are hardcoded in the app logic. Read this file first when building the
scoring function described in section 2.2.

---

## 6. Build Prompts (paste into Claude Code / your coding assistant)

Your project already has this structure (from your screenshot):
```
Route_optimization_agent/
├── backend/
│   ├── .venv/
│   ├── app/              # FastAPI app goes here
│   ├── db/                # JSON data files (config.json, warehouse.json, etc.)
│   ├── .env
│   └── requirements.txt
├── frontend/
│   └── route-optimization/   # React + Vite app
│       ├── node_modules/
│       ├── public/
│       ├── src/
│       ├── index.html
│       ├── package.json
│       └── vite.config.js
└── prompts/
```

Since you have a real FastAPI backend + React frontend (not Streamlit), split the build
into two prompts — run the backend one first so the frontend has an API to call.

### 6a. Backend prompt (run against `backend/app/`)

```
Build a FastAPI backend (in backend/app/) for a Warehouse Route Planner, orchestrated
internally by Microsoft Agent Framework (MAF) — same framework and setup already used
in this account's EAD Agent project, so match its conventions where applicable. The
project already has a data folder at backend/db/ containing: config.json,
warehouse.json, vehicles.json, drivers.json, stores.json, shipments.json, and
route_plan_sample.json (see schema below). Requirements:

1. Write a data_access.py module that loads all JSON files from backend/db/ using
   the paths listed in config.json's "data_files" section — never hardcode file
   paths elsewhere in the app.

2. Define three MAF tools (functions registered with the agent, each with a clear
   docstring/schema so the agent can decide when to call them):
   - `optimize_routes_tool`: wraps the OR-Tools VRP solver. Takes shipments, fleet,
     distance/time matrix, returns route plans (fastest/cheapest/balanced) per the
     RoutePlan schema below. Pure function — input/output as plain dicts, no
     OR-Tools objects crossing the boundary.
   - `get_route_matrix_tool`: wraps OpenRouteService Matrix API calls (distance/time
     between warehouse and stores) plus Nominatim geocoding for any store missing
     lat/lon. API key read from the env var named in config.json's
     api_config.routing_api_key_env_var, loaded from backend/.env.
   - `get_weather_tool`: wraps Open-Meteo calls for the delivery zones (no key
     needed).

3. Create an MAF agent (e.g. `route_planner_agent`) registered with these three
   tools plus a system prompt describing its job: "Given today's shipments and
   fleet, produce optimized route plans and explain trade-offs between them."
   The agent should be able to call the tools in sequence (matrix → weather →
   solve) and also answer free-text follow-up questions about a generated plan
   using the tool outputs already gathered as context (for the optional /api/ask
   endpoint).

4. Read vehicles.json (filter to status == "available") and drivers.json (join on
   assigned_driver_id) to build the fleet payload passed to the agent.

5. Read shipments.json for today's orders and join with stores.json on store_id to
   get delivery coordinates, zone, and receiving hours — this becomes the demand
   payload passed to the agent.

6. Expose these REST endpoints (add CORS middleware allowing the Vite dev server
   origin, typically http://localhost:5173). Each endpoint is a thin FastAPI layer
   that invokes the MAF agent — it should not call OR-Tools/ORS/Open-Meteo directly;
   all of that goes through the agent's tools:
   - GET  /api/shipments        → today's shipments joined with store details
   - GET  /api/fleet            → available vehicles joined with drivers
   - GET  /api/weather          → invokes get_weather_tool for delivery zones
   - POST /api/plan-routes      → invokes route_planner_agent, which calls
                                    get_route_matrix_tool then optimize_routes_tool,
                                    returns all 3 plans (fastest/cheapest/balanced)
                                    matching the RoutePlan schema below, including
                                    per-stop lat/lon and per-leg distance/duration so
                                    the frontend can render hover tooltips without
                                    recomputing anything
   - POST /api/approve-route    → body: { plan_id }. Writes the selected plan into
                                    backend/db/route_plan_sample.json (status:
                                    "approved") and updates matching shipments in
                                    shipments.json with assigned_plan_id and
                                    assigned_vehicle_id. This is a plain data write,
                                    not an agent call.
   - POST /api/ask              → body: { question, plan_id }. Invokes
                                    route_planner_agent with the question and the
                                    already-generated plan as context, returns a
                                    natural-language answer.

7. For each plan compute totals matching route_plan_sample.json's schema exactly:
   total_distance_km, total_duration_min, total_fuel_cost_inr (using
   config.json's default_fuel_price_inr_per_l and each vehicle's
   fuel_efficiency_km_per_l), total_co2_emissions_kg (using config.json's
   co2_emission_factor_kg_per_km per vehicle type), makespan_min, on_time_pct.
   Also compute per-leg distance_km/duration_min between consecutive stops (not
   just per-stop totals) — the frontend needs this for hover tooltips on each
   polyline segment.

8. Compute an effectiveness_score per plan using the weights in config.json's
   effectiveness_score_weights (distance/time/fuel_cost/emissions).

9. Handle errors gracefully: if optimize_routes_tool returns "infeasible", the
   agent/endpoint should return a 422 with a clear message explaining likely cause
   (e.g., time windows too tight, capacity exceeded) — don't let the API 500.

10. Keep all API keys in backend/.env (already exists), loaded via python-dotenv,
    never hardcoded, and never write real keys into any file under backend/db/.

11. Use only free/open-source libraries: fastapi, uvicorn, ortools, requests,
    python-dotenv, and the agent-framework package (same version as the EAD Agent
    project). Add them to backend/requirements.txt.

Deliver as:
backend/
├── app/
│   ├── main.py               # FastAPI app + route registration + CORS
│   ├── agent.py               # MAF agent definition + tool registration
│   ├── tools.py                # optimize_routes_tool, get_route_matrix_tool,
│   │                            # get_weather_tool implementations
│   ├── data_access.py         # loads/saves JSON from db/
│   └── schemas.py             # Pydantic models matching the schema below
├── db/                        # existing JSON data files (do not restructure)
└── requirements.txt           # updated with new dependencies
```

### 6b. Frontend prompt (run against `frontend/route-optimization/`)

```
Build the Route Planner screen in this existing React + Vite app
(frontend/route-optimization/). The backend is a FastAPI server (assume it runs at
http://localhost:8000) exposing: GET /api/shipments, GET /api/fleet,
GET /api/weather, POST /api/plan-routes, POST /api/approve-route,
POST /api/ask. Requirements:

1. Install and use react-leaflet + leaflet for the map (free, open-source — do not
   use any paid map SDK).
2. Build a RoutePlanner page/component with three sections:
   - A sidebar showing today's shipments (from GET /api/shipments), fleet summary
     (from GET /api/fleet), and current weather (from GET /api/weather)
   - A Leaflet map showing the warehouse marker, all store markers, and — once
     POST /api/plan-routes returns — each route plan drawn as a distinct colored
     polyline (e.g. blue = fastest, green = cheapest, orange = balanced), with a
     checkbox per plan to toggle its visibility
   - A comparison table below the map, one row per plan, columns: plan name,
     total distance, total duration, fuel cost, emissions, effectiveness score.
     Clicking a row highlights (bolds/widens) that plan's polyline on the map and
     dims the others.
3. Hover interactivity on the map:
   - Render each route as separate <Polyline> segments per leg (not one polyline
     for the whole route), so each leg can carry its own hover tooltip showing:
     from stop, to stop, leg distance (km), leg duration (min), and ETA at the
     destination stop. Use react-leaflet's <Tooltip sticky> so it follows the
     cursor while hovering over that segment.
   - On hover, increase that segment's stroke width slightly so the highlighted
     leg is visually obvious.
   - Hovering over a store marker shows a tooltip/popup with that stop's shipment
     details: store name, weight_kg, time window, and priority.
   - Hovering over the warehouse marker shows the warehouse name and address.
4. A "Generate Plans" button that calls POST /api/plan-routes and populates the
   map + table with the response.
5. An "Approve Route" button (enabled once a row is selected) that calls
   POST /api/approve-route with the selected plan_id, then shows a success state.
6. Handle the backend's 422 "infeasible" response by showing a clear inline error
   message instead of a blank screen.
7. Use plain fetch or axios for API calls (whichever is already a dependency;
   otherwise add axios). Keep the backend base URL in a .env file
   (VITE_API_BASE_URL=http://localhost:8000) — never hardcode it in components.
8. Match the existing project's code style (check src/ for existing conventions —
   component structure, CSS approach, linting rules in .oxlintrc.json) rather than
   introducing a new pattern.
9. Keep it functional-component + hooks based React; no class components.

Deliver as new/updated files under frontend/route-optimization/src/, e.g.:
src/
├── pages/RoutePlanner.jsx (or .tsx if the project uses TypeScript)
├── components/ShipmentSidebar.jsx
├── components/RouteMap.jsx
├── components/PlanComparisonTable.jsx
├── api/routeOptimizerApi.js
└── .env                      # VITE_API_BASE_URL=http://localhost:8000
```

---

## 6c. RoutePlan response schema (for both prompts to agree on)

```yaml
RoutePlan:
  plan_id: str
  plan_name: str                # fastest | cheapest | balanced
  routes:
    - vehicle_id: str
      driver_id: str
      stops:
        - store_id: str
          shipment_id: str
          store_name: str
          eta: str               # "09:20"
          lat: float
          lon: float
          load_after_stop_kg: float
      legs:                      # one entry per polyline segment, for hover tooltips
        - from_stop: str         # store_id or "WH001" for warehouse
          to_stop: str
          from_lat: float
          from_lon: float
          to_lat: float
          to_lon: float
          distance_km: float
          duration_min: float
      distance_km: float
      duration_min: float
      fuel_cost_inr: float
      co2_emissions_kg: float
      capacity_used_pct: float
  totals:
    total_distance_km: float
    total_duration_min: float
    total_fuel_cost_inr: float
    total_co2_emissions_kg: float
    makespan_min: float
    on_time_pct: float
  effectiveness_score: float
  status: str                    # draft | approved
```
Note the addition of `lat`/`lon` on each stop, `store_name`, and a `legs` array per
route compared to the stored `route_plan_sample.json` — the frontend needs coordinates
to draw polylines and per-leg distance/duration to power the hover tooltips, so the
backend's `/api/plan-routes` response should enrich the plan with this data even though
the persisted file doesn't need to duplicate all of it.

---

## 7. Suggested Build Order

1. Backend: data_access.py + endpoints for /api/shipments, /api/fleet (get data
   flowing before touching the solver)
2. Backend: distance/duration matrix via ORS + geocoding fallback
3. Backend: OR-Tools solver wired into /api/plan-routes (single "balanced" plan first)
4. Test backend endpoints directly (curl/Postman) before touching the frontend
5. Frontend: sidebar + map showing static shipment/store markers (no routes yet)
6. Frontend: wire up /api/plan-routes, draw polylines, build comparison table
7. Backend: add "fastest"/"cheapest" plan variants + weather integration
8. Frontend + backend: approve/persist flow via /api/approve-route
9. (Optional) "Ask AI" endpoint + frontend box, via local Ollama model