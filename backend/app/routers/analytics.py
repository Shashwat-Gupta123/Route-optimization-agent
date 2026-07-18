"""Component 3 API router — analytics KPI dashboard.

Thin FastAPI shell over :mod:`app.agent.analytics_service`. Registered as a
dedicated :class:`~fastapi.APIRouter` (like Component 2's monitoring router) so
the analytics endpoints stay separate from Components 1 and 2.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.core_logger import get_logger
from app.agent import analytics_service
from app.agent.model.schemas import SendReportRequest, SendReportResponse

logger = get_logger("analytics_router")

router = APIRouter(prefix="/api/kpis", tags=["analytics"])


@router.get("/summary")
def summary(
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
) -> dict:
    """Aggregated KPI-card data for the selected range."""
    try:
        return analytics_service.summary(from_, to)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/trends")
def trends(
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
) -> dict:
    """Daily time-series for the trend charts."""
    try:
        return analytics_service.trends(from_, to)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/cost-breakdown")
def cost_breakdown(
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
) -> dict:
    """Fuel vs labour vs vehicle-wear share of total delivery cost."""
    try:
        return analytics_service.cost_breakdown(from_, to)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/weather-correlation")
def weather_correlation() -> dict:
    """Average delay grouped by weather condition."""
    return analytics_service.weather_correlation()


@router.post("/send-report", response_model=SendReportResponse)
def send_report(body: SendReportRequest) -> SendReportResponse:
    """Email a KPI summary and post a dashboard digest alert."""
    try:
        result = analytics_service.send_report(body.from_, body.to, body.email)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return SendReportResponse(
        status=result["status"],
        message=result["message"],
        alert=result.get("alert"),
    )
