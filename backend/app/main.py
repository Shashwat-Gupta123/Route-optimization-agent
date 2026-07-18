"""FastAPI application for the Warehouse Route Planner (Component 1).

Each endpoint is a thin layer over :mod:`app.agent.service`, which orchestrates
the MAF agent's tools (route matrix, weather, OR-Tools solver) and the data
access layer. CORS is enabled for the Vite dev server.

Endpoints
---------
* ``GET  /api/shipments``     today's shipments joined with store details
* ``GET  /api/fleet``         available vehicles joined with drivers
* ``GET  /api/weather``       current weather per delivery zone
* ``POST /api/plan-routes``   generate fastest/cheapest/balanced plans
* ``POST /api/approve-route`` persist the selected plan
* ``POST /api/ask``           natural-language Q&A about a plan
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app import config, data_access
from app.core_logger import get_logger
from app.agent import service
from app.agent.service import InfeasiblePlanError
from app.agent.tools.weather import get_weather_tool
from app.routers.monitoring import router as monitoring_router
from app.routers.analytics import router as analytics_router
from app.routers.chat import router as chat_router
from app.agent.model.schemas import (
    ApproveRouteRequest,
    ApproveRouteResponse,
    AskRequest,
    AskResponse,
    PlanRoutesResponse,
)

logger = get_logger("main")

app = FastAPI(title=config.get_config().get("app_name", "Warehouse Route Planner"), version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Component 2 — real-time monitoring & disruption handling.
app.include_router(monitoring_router)

# Component 3 — analytics KPI dashboard.
app.include_router(analytics_router)

# Component 5 — chat assistant.
app.include_router(chat_router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/warehouse")
def get_warehouse() -> dict:
    """Return the warehouse/depot record (coordinates, name, address)."""
    return data_access.load_warehouse()


@app.get("/api/route-plan")
def get_route_plan() -> dict:
    """Return the currently persisted (approved) route plan."""
    return data_access.load_route_plan()


@app.get("/api/shipments")
def get_shipments() -> list:
    """Return today's shipments joined with their store's delivery details."""
    return data_access.get_shipments_with_store()


@app.get("/api/fleet")
def get_fleet() -> list:
    """Return available vehicles joined with their assigned driver."""
    return data_access.get_available_fleet()


@app.get("/api/weather")
def get_weather() -> list:
    """Return current weather for each unique delivery zone (+ warehouse)."""
    warehouse = data_access.load_warehouse()
    shipments = data_access.get_shipments_with_store()
    zones = service._unique_zones(warehouse, shipments)
    return get_weather_tool(zones)


@app.post("/api/reset-shipments")
def reset_shipments() -> dict:
    """Reset all shipments to 'pending' status for demo/testing purposes.

    Clears ``status``, ``assigned_plan_id``, and ``assigned_vehicle_id`` from
    every shipment so route planning can be re-run from scratch.
    """
    shipments = data_access.reset_shipments()
    logger.info("Reset %d shipments to pending status.", len(shipments))
    return {"reset": len(shipments), "message": f"{len(shipments)} shipments reset to pending."}


@app.post("/api/plan-routes", response_model=PlanRoutesResponse)
async def plan_routes() -> PlanRoutesResponse:
    """Generate the fastest/cheapest/balanced route plans for today."""
    try:
        result = await service.plan_routes()
    except InfeasiblePlanError as exc:
        logger.warning("Plan infeasible: %s", exc)
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.error("plan-routes failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Route planning failed unexpectedly.")
    return PlanRoutesResponse(**result)


@app.post("/api/approve-route", response_model=ApproveRouteResponse)
def approve_route(body: ApproveRouteRequest) -> ApproveRouteResponse:
    """Persist the selected plan and mark its shipments as assigned."""
    try:
        service.approve_route(body.plan_id)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Plan '{body.plan_id}' not found. Generate plans before approving.",
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("approve-route failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to approve the route plan.")
    return ApproveRouteResponse(
        status="approved",
        plan_id=body.plan_id,
        message="Route plan approved and persisted.",
    )


@app.post("/api/ask", response_model=AskResponse)
async def ask(body: AskRequest) -> AskResponse:
    """Answer a free-text question about a generated plan using the MAF agent."""
    answer = await service.ask(body.question, body.plan_id)
    return AskResponse(answer=answer)
