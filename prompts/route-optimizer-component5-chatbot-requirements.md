# Route Optimizer — Component 5: Chatbot Query Assistant
## Detailed Requirements & Build Prompt

---

## 1. Purpose

Let the dispatch manager (or an executive glancing at the dashboard) ask free-text
questions about shipments, fleet, routes, alerts, and KPIs, and get back an answer
that is **grounded in real data**, not a plausible-sounding guess. This is the
highest-risk component from an accuracy standpoint — a wrong number in a chat answer
is worse than no chatbot at all — so the design below is built around one rule above
everything else:

> **The agent may only state a number, status, or fact if it came from a tool call
> against real data this turn. If no tool covers the question, it says so — it does
> not estimate, infer, or fall back on general knowledge.**

---

## 2. How it evaluates a query (the reasoning pipeline)

The diagram above shows the shape of it. In words:

1. **User question** arrives from the chat widget, along with recent conversation
   turns (for follow-ups like "what about tomorrow?") and optional **page context**
   — if the user is viewing a specific plan or date range when they ask, pass that
   `plan_id`/date range along so the agent doesn't have to ask "which plan?".
2. **Chat assistant agent** (a Microsoft Agent Framework agent with a strict system
   prompt — see 2.1) interprets the question: what is being asked, which entities
   are named (a store, a vehicle, a date range), and which registered tool(s) can
   answer it.
3. **Tool selection & execution** — the agent calls one or more read-only tools
   (grouped below into shipment/fleet, route/KPI, and alerts/weather). Each tool
   queries the actual `backend/db/*.json` files (the same files every other
   component reads/writes) and returns structured data — never prose.
4. **Grounded answer** — the agent composes a natural-language reply using only the
   values the tools returned, states which tool(s)/data it used (for the UI's small
   "sources" footnote), and — where relevant — suggests a concrete next action
   ("Want me to re-optimize VEH002's route?") rather than performing it itself.

### 2.1 System prompt requirements (the grounding contract)
The agent's system prompt must explicitly instruct it to:
- Only state facts/numbers that came from a tool result this turn.
- If no available tool can answer the question, say so plainly ("I don't have a data
  source for that yet") instead of guessing.
- Never call a tool that mutates data (approving a route, sending an alert,
  triggering a re-optimization) — this agent is **read-only** for v1. If the answer
  to a question implies an action, it should describe what could be done and point
  the user to the relevant button/page, not do it via chat.
- Always be explicit about the time window/scope of a number (e.g. "as of today
  09:35" or "for the last 7 days") since dispatch data changes throughout the day.

### 2.2 Prompt storage — YAML, not hardcoded in Python
The system prompt, guardrail list, refusal/redirect wording, and the tool allowlist
all live in a single YAML file, **not** as a string literal inside `agent.py`. This
keeps the prompt reviewable and diffable on its own, and means iterating on wording
doesn't require touching application logic.

```
backend/app/prompts/chat_assistant.yaml
```

Structure (see the attached file for the full version):
```yaml
agent_name: chat_assistant_agent
version: 1
last_updated: "2026-07-16"
system_prompt: |
  You are the warehouse operations assistant...
  (full grounding-contract rules from 2.1, written out in full)
guardrails:
  - no_unsourced_numbers
  - no_write_tool_calls
  - always_state_time_scope
  - refuse_out_of_scope_politely
response_templates:
  no_data_response: >
    I don't have a data source for that yet...
  action_redirect_template: >
    I can't do that from chat, but you can {action} from {page_or_button}.
  out_of_scope_response: >
    I can only help with questions about this warehouse's...
tool_allowlist:
  - query_shipments_tool
  - query_fleet_tool
  - query_route_plan_tool
  - query_alerts_tool
  - explain_plan_tool
  - compute_kpi_tool
  - get_weather_tool
```
`agent.py` loads this file at startup (`yaml.safe_load`) and builds the agent's system
prompt and tool registration from it — bump `version` whenever the prompt changes so
you can trace which prompt version produced a given answer if you're debugging a bad
response later.

---

## 3. Sample queries and how each gets evaluated

| User asks | Tool(s) called | What grounds the answer |
|---|---|---|
| "How many shipments are pending today?" | `query_shipments_tool(status=pending, date=today)` | Count + total weight from `shipments.json` |
| "What's in shipment SHP1002?" | `query_shipments_tool(shipment_id=SHP1002)` | Items, weight, time window from `shipments.json` |
| "Which vehicles are available right now?" | `query_fleet_tool(status=available)` | Vehicle list from `vehicles.json` joined with `drivers.json` |
| "Is any vehicle delayed right now?" | `query_fleet_tool` + vehicle location lookup | `eta_deviation_min` from `vehicle_locations.json` |
| "What caused the alert for VEH002?" | `query_alerts_tool(vehicle_id=VEH002)` | Alert message/type/severity from `alerts.json` |
| "What was the fuel cost for today's balanced plan?" | `query_route_plan_tool(plan_name=balanced)` | `total_fuel_cost_inr` from `route_plan_sample.json` |
| "Why did the fastest plan skip Store STR004 first?" | `query_route_plan_tool` + `explain_plan_tool` | Route order + distance/capacity figures from the plan, explained in plain language — not invented reasoning |
| "What was our on-time percentage last week?" | `compute_kpi_tool(range=last 7 days)` | Aggregated `on_time_pct` from `route_history.json` (reused from Component 3) |
| "How does rain affect our delivery times?" | `compute_kpi_tool` (weather correlation) | Average delay by `weather_condition` from `route_history.json` |
| "What's the weather in Ghaziabad zone today?" | `get_weather_tool(zone=Ghaziabad)` | Open-Meteo response (reused from Component 1) |
| "Can you approve today's balanced plan?" | *(none — refused)* | Agent explains this must be done via the "Approve Route" button on the Route Planner page, since chat is read-only |
| "What's the capital of France?" | *(none — out of scope)* | Agent explains it only answers questions about this warehouse's shipments, fleet, and routes |

This table is also the acceptance test suite — each row should have a working example
in your final build before calling Component 5 done.

---

## 4. New MAF tools (added to `backend/app/tools.py`, alongside existing ones)

- `query_shipments_tool(filters)`: filters `shipments.json` by `store_id`, `status`,
  `priority`, `date`, or `shipment_id`; returns matching records, joined with
  `stores.json` for store name/zone when relevant.
- `query_fleet_tool(filters)`: filters `vehicles.json` (+ `drivers.json` join) by
  `status`, `vehicle_id`; optionally merges in `vehicle_locations.json` for live
  status/ETA-deviation questions.
- `query_route_plan_tool(filters)`: looks up `route_plan_sample.json` (today's plan)
  or a specific day in `route_history.json`, by `plan_name`, `plan_id`, or `date`.
- `query_alerts_tool(filters)`: filters `alerts.json` by `vehicle_id`, `severity`,
  `type`, or `acknowledged` status.
- `explain_plan_tool`: given a plan (from `query_route_plan_tool`), produces a
  natural-language explanation of routing decisions using the plan's own
  distance/capacity/time-window data — this is reasoning *about retrieved data*, not
  new information.
- Reused as-is from earlier components: `compute_kpi_tool` (Component 3),
  `get_weather_tool` (Component 1).

**Deliberately not exposed to this agent**: `optimize_routes_tool`,
`reoptimize_remaining_tool`, `send_alert_tool`, or anything that writes to
`backend/db/`. Keeping the chat agent read-only is a safety choice, not an oversight
— an executive typing a casually-worded question should never accidentally trigger a
re-plan or an email blast.

---

## 5. Backend endpoints

- `POST /api/chat` → body: `{ message, conversation_id, page_context? }`. Runs the
  chat assistant agent, returns:
  ```json
  {
    "reply": "There are 6 pending shipments today, totaling 1,230 kg.",
    "sources_used": ["query_shipments_tool"],
    "suggested_follow_ups": ["Which store has the heaviest shipment?"]
  }
  ```
- `GET /api/chat/history?conversation_id=...` → returns that individual session's
  prior turns only (see 5.1) — never another session's data, even if requested in
  the same time window.

`conversation_id` is a UUID the frontend generates once per browser session (kept in
React state, not localStorage/sessionStorage) and sent with every message so the
backend can retrieve that specific session's recent turns for follow-up context.

### 5.1 Conversation history storage — isolated per conversation_id
Each individual conversation is stored under its own key — histories are never
merged, shared, or readable across `conversation_id` values. This matters both for
correctness (one user's follow-up context shouldn't leak into another user's
session) and for the "what about tomorrow?" follow-up pattern to work reliably.

```
backend/db/chat_sessions.json
```

Schema (see the attached seed file for a full worked example):
```yaml
sessions:
  <conversation_id>:
    started_at: <ISO timestamp>
    last_active_at: <ISO timestamp>
    page_context: { page, plan_id }        # optional, whatever the frontend sent
    turns:
      - turn_id: int
        role: "user" | "assistant"
        message: str
        timestamp: <ISO timestamp>
        sources_used: [tool names]          # assistant turns only
        suggested_follow_ups: [str]          # assistant turns only
```

Implementation notes:
- Look up `sessions[conversation_id]` directly — never scan/filter across all
  sessions to find a match.
- When building the agent's context for a new message, pass only that
  `conversation_id`'s own `turns` (e.g. the last 6–10) — not the whole file.
- A `conversation_id` with no existing entry just means "new session" — create it,
  don't error.
- This file-per-app (not file-per-conversation) approach is fine at demo scale; if
  session volume grows later, the natural next step is one row per conversation in a
  real database, but the isolation contract (`sessions[conversation_id]` only) stays
  identical either way.

---

## 6. Backend build prompt (run against `backend/app/`)

```
Extend the existing FastAPI + Microsoft Agent Framework backend with a read-only
conversational query assistant. Requirements:

1. Add a new MAF agent, chat_assistant_agent, in backend/app/agent.py. Do NOT
   hardcode its system prompt as a Python string — load it, along with guardrails,
   response templates, and the tool allowlist, from
   backend/app/prompts/chat_assistant.yaml (use PyYAML's yaml.safe_load) at
   startup. Add pyyaml to requirements.txt if not already present.

2. Register chat_assistant_agent with exactly the tools listed in the YAML file's
   tool_allowlist — do not give it access to optimize_routes_tool,
   reoptimize_remaining_tool, send_alert_tool, or any tool that writes to
   backend/db/:
   - query_shipments_tool(filters): filters shipments.json by store_id, status,
     priority, date, or shipment_id; joins stores.json for store name/zone.
   - query_fleet_tool(filters): filters vehicles.json + drivers.json by status,
     vehicle_id; optionally merges vehicle_locations.json for live status/ETA
     deviation.
   - query_route_plan_tool(filters): looks up route_plan_sample.json or a specific
     day in route_history.json by plan_name, plan_id, or date.
   - query_alerts_tool(filters): filters alerts.json by vehicle_id, severity, type,
     acknowledged.
   - explain_plan_tool: given a plan object, generates a natural-language
     explanation of its routing decisions using only that plan's own data.
   - compute_kpi_tool and get_weather_tool: reuse the existing implementations from
     the Analytics and Route Planner components rather than duplicating logic.

3. Expose POST /api/chat: body { message: str, conversation_id: str,
   page_context: dict | None }. Persist conversation turns in
   backend/db/chat_sessions.json under sessions[conversation_id] — see the schema
   in the requirements doc (section 5.1). Each conversation_id's turns must stay
   isolated: look up and update only that key, never scan or merge across sessions.
   When building context for the agent, pass only that conversation's own recent
   turns (last 6-10). A conversation_id with no existing entry means a new session
   — create it rather than erroring. Response shape:
   { "reply": str, "sources_used": [tool names called], "suggested_follow_ups":
   [2-3 short strings] }.

4. Expose GET /api/chat/history?conversation_id=... returning that individual
   session's turns only (sessions[conversation_id]["turns"]), for the frontend to
   restore state on reload.

5. If the agent determines no available tool can answer the question, the reply
   must say so plainly instead of the model generating a best-guess answer — this
   is a hard requirement, not a nice-to-have. Add a lightweight check in
   chat_assistant_agent's response handling: if sources_used is empty AND the
   question implied a factual/numeric claim, that's a bug to catch, not a valid
   response — the system prompt plus tool availability should make this rare, but
   log any occurrence for review.

6. If the question asks for an action the agent can't perform (approving a route,
   sending an alert, triggering re-optimization), the reply should name the correct
   page/button instead of a refusal with no path forward — e.g. "You can approve
   this from the Route Planner page's Approve Route button."

7. Use only free/open-source tooling — no new paid dependency required; this reuses
   the same agent-framework package already in requirements.txt.
```

---

## 7. Frontend build prompt (run against `frontend/route-optimization/`)

```
Add a floating chat assistant to this React + Vite app, available on every page via
the AppShell (alongside the alerts bell built in the frontend shell prompt).
Requirements:

1. Floating chat launcher: a circular button fixed to the bottom-right corner (same
   corner convention as MAQ Software's own site chat widget), using
   var(--color-primary) red as its background, a chat/message icon, visible on
   every page. Clicking it expands a chat panel (slide-up or slide-in from the
   corner) without navigating away from the current page.

2. Chat panel contents:
   - Scrollable message list (user messages right-aligned, assistant messages
     left-aligned), rendering conversation history from GET /api/chat/history on
     first open.
   - A small "sources" line under each assistant message when sources_used is
     non-empty (e.g. "Based on: shipment data" or "Based on: route plan, KPI
     data") — this is a trust signal, keep it subtle (muted gray text, not a badge).
   - Suggested follow-up chips below the latest assistant message, populated from
     suggested_follow_ups — clicking one sends it as the next message.
   - A row of starter-query chips shown when the conversation is empty (pull 3-4
     examples from the sample query table in the requirements doc, e.g. "How many
     shipments are pending today?", "Is any vehicle delayed?", "What was our
     on-time % last week?") so users who don't know what to ask have a starting
     point.
   - Text input + send button; show a lightweight "thinking" indicator (not a fake
     progress bar) while waiting for POST /api/chat to respond.

3. Generate a conversation_id (UUID) once per app load, store it in React state
   (not localStorage/sessionStorage), and send it with every POST /api/chat call.
   If page_context is available (e.g. user has a plan open on the Route Planner
   page), include it in the request body.

4. Handle the "agent doesn't have data for this" case as a normal assistant
   message, not an error state — it's a valid, expected response type.

5. Match the MAQ-brand design system already defined for this app (section 2.4 of
   the frontend app requirements doc) — the chat bubble and panel should look like
   part of the same product as the rest of the dashboard, not a bolted-on
   third-party widget.

6. Match existing project conventions (component structure, styling, linting).
   Functional components + hooks only.

Deliver as:
src/
├── components/
│   └── chat/
│       ├── ChatLauncher.jsx      # floating button
│       ├── ChatPanel.jsx          # message list + input + chips
│       └── ChatMessage.jsx        # single message bubble + sources line
├── hooks/
│   └── useChat.js                 # conversation state, sends/receives, history load
```

---

## 8. Free API keys / setup needed

None beyond what earlier components already use. The chat assistant reuses the same
`agent-framework` package and, if you're running a local LLM for reasoning (as
established for the "Reasoning layer" in the original architecture), the same Ollama
setup — no new signup, no new key. Add `pyyaml` to `requirements.txt` for loading the
prompt file (section 2.2).

---

## 9. End-to-end test script — run this after the build

Once both the backend and frontend prompts have been run, verify Component 5 works
by exercising these requests directly against the backend (curl or any HTTP client)
before testing through the UI — it isolates agent/tool bugs from frontend bugs. Use a
fresh `conversation_id` (any UUID) for the first request, then reuse it for the
follow-up to confirm conversation isolation and context work.

**Test 1 — basic grounded lookup**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How many shipments are pending today?", "conversation_id": "test-001"}'
```
Expect: `sources_used` includes `query_shipments_tool`, and the reply states an actual
count that matches what's in `shipments.json` — not a rounded or generic-sounding
number.

**Test 2 — follow-up using conversation context**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Which one is heaviest?", "conversation_id": "test-001"}'
```
Expect: the agent correctly resolves "which one" to refer to the pending shipments
from Test 1, without you having to restate "shipments" — confirms `chat_sessions.json`
context passing works.

**Test 3 — isolation check**
```bash
curl "http://localhost:8000/api/chat/history?conversation_id=test-001"
```
Then repeat with a conversation_id that was never used, e.g. `test-999`. Expect: the
second call returns an empty/new session, never Test 1/2's turns — confirms sessions
don't leak into each other.

**Test 4 — analytics/aggregation**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What was our on-time percentage last week?", "conversation_id": "test-002"}'
```
Expect: `sources_used` includes `compute_kpi_tool`, and the figure matches what
`GET /api/kpis/summary` returns for the same range (cross-check against Component 3's
endpoint directly).

**Test 5 — refusal: no data source**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the capital of France?", "conversation_id": "test-003"}'
```
Expect: `sources_used` is empty, and the reply matches (or closely follows)
`out_of_scope_response` from the YAML prompt file — not an actual answer about France.

**Test 6 — refusal: action request redirected, not performed**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Approve todays balanced plan", "conversation_id": "test-004"}'
```
Expect: the reply names the Route Planner page's Approve Route button, and —
critically — confirm via `GET /api/kpis/summary` or `route_plan_sample.json` directly
that the plan's `status` field did NOT change to `"approved"`. This is the most
important test in this list: it proves the read-only boundary actually holds and
isn't just a polite-sounding prompt instruction.

**Remaining coverage**: run the rest of the rows from the section 3 table
("Is any vehicle delayed?", "What caused the alert for VEH002?", "Why did the fastest
plan skip Store STR004 first?", "How does rain affect our delivery times?") the same
way — each should come back with a non-empty `sources_used` matching the tool listed
in that row, and a reply whose numbers you can verify by opening the underlying JSON
file directly.