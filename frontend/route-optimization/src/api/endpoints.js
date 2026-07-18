import client from "./client";

/**
 * Grouped API calls for all three components. Every request goes through the
 * shared Axios `client` (base URL from env, normalized errors), so no component
 * builds its own URLs or re-implements error parsing.
 */

// --- Component 1: Route Planner ---------------------------------------------
export const getWarehouse = () =>
    client.get("/api/warehouse").then((r) => r.data);
export const getShipments = () =>
    client.get("/api/shipments").then((r) => r.data);
export const getFleet = () => client.get("/api/fleet").then((r) => r.data);
export const getWeather = () => client.get("/api/weather").then((r) => r.data);
export const planRoutes = () =>
    client.post("/api/plan-routes").then((r) => r.data);
export const approveRoute = (planId) =>
    client.post("/api/approve-route", { plan_id: planId }).then((r) => r.data);
export const askAi = (question, planId) =>
    client.post("/api/ask", { question, plan_id: planId }).then((r) => r.data);
export const resetShipments = () =>
    client.post("/api/reset-shipments").then((r) => r.data);

// --- Component 2: Live Monitoring -------------------------------------------
export const getRoutePlan = () =>
    client.get("/api/route-plan").then((r) => r.data);
export const getVehicleLocations = () =>
    client.get("/api/vehicle-locations").then((r) => r.data);
export const simulateTrafficJam = (vehicleId, delayMin) =>
    client
        .post("/api/simulate/traffic-jam", {
            vehicle_id: vehicleId,
            delay_min: delayMin,
        })
        .then((r) => r.data);
export const simulateBreakdown = (vehicleId) =>
    client
        .post("/api/simulate/breakdown", { vehicle_id: vehicleId })
        .then((r) => r.data);
export const addUrgentOrder = (payload) =>
    client.post("/api/simulate/urgent-order", payload).then((r) => r.data);
export const reoptimize = (payload) =>
    client.post("/api/reoptimize", payload).then((r) => r.data);
export const confirmReoptimize = (planId) =>
    client
        .post("/api/reoptimize/confirm", { plan_id: planId })
        .then((r) => r.data);

// --- Component 3: Analytics -------------------------------------------------
export const getKpiSummary = (from, to) =>
    client
        .get("/api/kpis/summary", { params: { from, to } })
        .then((r) => r.data);
export const getKpiTrends = (from, to) =>
    client
        .get("/api/kpis/trends", { params: { from, to } })
        .then((r) => r.data);
export const getCostBreakdown = (from, to) =>
    client
        .get("/api/kpis/cost-breakdown", { params: { from, to } })
        .then((r) => r.data);
export const getWeatherCorrelation = () =>
    client.get("/api/kpis/weather-correlation").then((r) => r.data);
export const sendReport = (from, to, email) =>
    client.post("/api/kpis/send-report", { from, to, email }).then((r) => r.data);

// --- Component 5: Chat Assistant --------------------------------------------
export const postChat = (message, conversationId, pageContext = null) =>
    client
        .post("/api/chat", {
            message,
            conversation_id: conversationId,
            page_context: pageContext,
        })
        .then((r) => r.data);
export const getChatHistory = (conversationId) =>
    client
        .get("/api/chat/history", { params: { conversation_id: conversationId } })
        .then((r) => r.data);

