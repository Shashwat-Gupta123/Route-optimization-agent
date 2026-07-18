"""Pydantic models for the Route Planner API.

These mirror the JSON schema described in the component-1 requirements. The
``RoutePlan`` response is enriched (vs. the persisted ``route_plan_sample.json``)
with per-stop ``lat``/``lon``, ``store_name`` and a ``legs`` array so the React
frontend can draw polylines and per-leg hover tooltips without recomputing.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# --- Route plan (solver output) ---------------------------------------------

class Stop(BaseModel):
    store_id: str
    shipment_id: str
    store_name: str
    eta: str  # "09:20"
    lat: float
    lon: float
    load_after_stop_kg: float


class Leg(BaseModel):
    """One polyline segment between two consecutive points on a route."""

    from_stop: str  # store_id or warehouse_id
    to_stop: str
    from_name: str
    to_name: str
    from_lat: float
    from_lon: float
    to_lat: float
    to_lon: float
    distance_km: float
    duration_min: float
    eta: str  # ETA at the destination stop


class VehicleRoute(BaseModel):
    vehicle_id: str
    driver_id: Optional[str] = None
    driver_name: Optional[str] = None
    vehicle_type: Optional[str] = None
    stops: List[Stop]
    legs: List[Leg]
    distance_km: float
    duration_min: float
    fuel_cost_inr: float
    co2_emissions_kg: float
    capacity_used_pct: float


class RouteTotals(BaseModel):
    total_distance_km: float
    total_duration_min: float
    total_fuel_cost_inr: float
    total_co2_emissions_kg: float
    makespan_min: float
    on_time_pct: float


class RoutePlan(BaseModel):
    plan_id: str
    plan_name: str  # fastest | cheapest | balanced
    warehouse_id: str
    generated_at: str
    routes: List[VehicleRoute]
    totals: RouteTotals
    effectiveness_score: float
    status: str = "draft"  # draft | approved


# --- API request/response models --------------------------------------------

class PlanRoutesResponse(BaseModel):
    plans: List[RoutePlan]
    weather: List[Dict[str, Any]] = Field(default_factory=list)
    summary: Optional[str] = None


class ApproveRouteRequest(BaseModel):
    plan_id: str


class ApproveRouteResponse(BaseModel):
    status: str
    plan_id: str
    message: str


class AskRequest(BaseModel):
    question: str
    plan_id: Optional[str] = None


class AskResponse(BaseModel):
    answer: str


# --- Component 2: real-time monitoring & disruption handling -----------------

class SimulateTrafficJamRequest(BaseModel):
    vehicle_id: str
    delay_min: float = Field(gt=0, description="Minutes of ETA delay to add.")


class SimulateBreakdownRequest(BaseModel):
    vehicle_id: str


class UrgentOrderRequest(BaseModel):
    """Fields for injecting an urgent shipment into the pending pool."""

    store_id: str
    weight_kg: float = Field(gt=0)
    latest_delivery_time: str  # "HH:MM"
    earliest_delivery_time: str = "00:00"
    priority: str = "high"
    volume_m3: float = 0.0
    special_handling: bool = False


class AcknowledgeAlertResponse(BaseModel):
    status: str
    alert_id: str


class SimpleActionResponse(BaseModel):
    """Generic response for a simulate/* action plus any alert it raised."""

    status: str
    message: str
    vehicle: Optional[Dict[str, Any]] = None
    alert: Optional[Dict[str, Any]] = None
    affected_shipment_ids: List[str] = Field(default_factory=list)


class ReoptimizeRequest(BaseModel):
    vehicle_id: Optional[str] = None
    affected_vehicle_ids: Optional[List[str]] = None


class RouteComparison(BaseModel):
    """Before/after summary for a re-optimization preview."""

    distance_km: float
    duration_min: float
    stop_count: int
    affected_stores: List[str] = Field(default_factory=list)


class ReoptimizeResponse(BaseModel):
    plan_id: str
    before: RouteComparison
    after: RouteComparison
    plan: RoutePlan


class ReoptimizeConfirmRequest(BaseModel):
    plan_id: str


class ReoptimizeConfirmResponse(BaseModel):
    status: str
    plan_id: str
    message: str
    notified_stores: List[str] = Field(default_factory=list)


# --- Component 3: analytics dashboard ----------------------------------------

class SendReportRequest(BaseModel):
    from_: str = Field(alias="from")
    to: str

    model_config = {"populate_by_name": True}


class SendReportResponse(BaseModel):
    status: str
    message: str
    alert: Optional[Dict[str, Any]] = None
