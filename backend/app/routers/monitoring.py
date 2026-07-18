"""Component 2 API router — real-time monitoring & disruption handling.

Kept separate from Component 1's endpoints (registered in :mod:`app.main`) via a
dedicated :class:`~fastapi.APIRouter`. Each endpoint is a thin shell over
:mod:`app.agent.monitoring_service`, which coordinates the monitoring tools and
the data-access layer.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core_logger import get_logger
from app.agent import monitoring_service
from app.agent.model.schemas import (
    AcknowledgeAlertResponse,
    ReoptimizeConfirmRequest,
    ReoptimizeConfirmResponse,
    ReoptimizeRequest,
    ReoptimizeResponse,
    SimpleActionResponse,
    SimulateBreakdownRequest,
    SimulateTrafficJamRequest,
    UrgentOrderRequest,
)

logger = get_logger("monitoring_router")

router = APIRouter(prefix="/api", tags=["monitoring"])


@router.get("/vehicle-locations")
def vehicle_locations() -> dict:
    """Current simulated positions + status for all vehicles."""
    return monitoring_service.get_vehicle_locations()


@router.post("/simulate/traffic-jam", response_model=SimpleActionResponse)
def simulate_traffic_jam(body: SimulateTrafficJamRequest) -> SimpleActionResponse:
    """Apply an ETA delay to a vehicle; alert if it breaches the threshold."""
    try:
        result = monitoring_service.simulate_traffic_jam(body.vehicle_id, body.delay_min)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Vehicle '{body.vehicle_id}' not found.")
    return SimpleActionResponse(
        status=result["status"],
        message=result["message"],
        vehicle=result.get("vehicle"),
        alert=result.get("alert"),
    )


@router.post("/simulate/breakdown", response_model=SimpleActionResponse)
def simulate_breakdown(body: SimulateBreakdownRequest) -> SimpleActionResponse:
    """Mark a vehicle broken down, flag its shipments, raise a critical alert."""
    try:
        result = monitoring_service.simulate_breakdown(body.vehicle_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Vehicle '{body.vehicle_id}' not found.")
    return SimpleActionResponse(
        status=result["status"],
        message=result["message"],
        vehicle=result.get("vehicle"),
        alert=result.get("alert"),
        affected_shipment_ids=result.get("affected_shipment_ids", []),
    )


@router.post("/simulate/urgent-order", response_model=SimpleActionResponse)
def simulate_urgent_order(body: UrgentOrderRequest) -> SimpleActionResponse:
    """Inject a new pending shipment into the pool for the next re-optimization."""
    result = monitoring_service.add_urgent_order(body.model_dump())
    return SimpleActionResponse(
        status=result["status"],
        message=result["message"],
        alert=result.get("alert"),
    )


@router.get("/alerts")
def alerts() -> list:
    """List alerts, most recent first."""
    return monitoring_service.list_alerts()


@router.post("/alerts/{alert_id}/acknowledge", response_model=AcknowledgeAlertResponse)
def acknowledge(alert_id: str) -> AcknowledgeAlertResponse:
    """Mark an alert acknowledged."""
    try:
        monitoring_service.acknowledge_alert(alert_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found.")
    return AcknowledgeAlertResponse(status="acknowledged", alert_id=alert_id)


@router.post("/reoptimize", response_model=ReoptimizeResponse)
def reoptimize(body: ReoptimizeRequest) -> ReoptimizeResponse:
    """Preview a re-optimization of the remaining stops (does not persist)."""
    try:
        result = monitoring_service.reoptimize(body.vehicle_id, body.affected_vehicle_ids)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Vehicle '{exc.args[0]}' not found.")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return ReoptimizeResponse(**result)


@router.post("/reoptimize/confirm", response_model=ReoptimizeConfirmResponse)
def reoptimize_confirm(body: ReoptimizeConfirmRequest) -> ReoptimizeConfirmResponse:
    """Persist a previewed re-optimization and notify affected stores."""
    try:
        result = monitoring_service.confirm_reoptimize(body.plan_id)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Re-optimization '{body.plan_id}' not found or already confirmed.",
        )
    return ReoptimizeConfirmResponse(**result)
