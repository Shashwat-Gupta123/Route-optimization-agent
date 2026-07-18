"""Analytics KPI service (Component 3).

Aggregates the historical planned-vs-actual daily performance records in
``route_history.json`` (plus today's approved plan when its date falls in the
selected range) into the KPI cards, trend series, cost breakdown and
weather-correlation views the Analytics Dashboard renders.

Kept as a thin orchestration layer (mirroring :mod:`app.agent.service` and
:mod:`app.agent.monitoring_service`) so the analytics router stays a thin
FastAPI shell. Date ranges are validated here and surfaced as ``ValueError`` for
the router to translate into a 400.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from app import data_access
from app.config import get_config
from app.core_logger import get_logger
from app.agent.tools.send_alert import send_alert_tool

logger = get_logger("analytics")


def _parse_date(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid date '{value}'. Expected YYYY-MM-DD.") from exc


def _shift_hours(shift: str) -> float:
    """Return the number of hours in a ``HH:MM-HH:MM`` shift string."""
    try:
        start_s, end_s = shift.split("-")
        start = datetime.strptime(start_s.strip(), "%H:%M")
        end = datetime.strptime(end_s.strip(), "%H:%M")
        hours = (end - start).total_seconds() / 3600.0
        return hours if hours > 0 else 0.0
    except (ValueError, AttributeError):
        return 0.0


def _today_history_entry() -> Optional[Dict[str, Any]]:
    """Derive a history-shaped record from today's approved plan, if present."""
    try:
        plan = data_access.load_route_plan()
    except FileNotFoundError:
        return None
    if not plan or plan.get("status") != "approved":
        return None

    generated = plan.get("approved_at") or plan.get("generated_at") or ""
    date = generated[:10] if generated else datetime.now().strftime("%Y-%m-%d")
    totals = plan.get("totals", {})
    shipments = sum(len(r.get("stops", [])) for r in plan.get("routes", []))
    caps = [r.get("capacity_used_pct", 0.0) for r in plan.get("routes", [])]
    utilization = round(sum(caps) / len(caps), 1) if caps else 0.0
    fuel = totals.get("total_fuel_cost_inr", 0.0)
    return {
        "date": date,
        "weather_condition": "clear",
        "shipments_delivered": shipments,
        "total_distance_planned_km": totals.get("total_distance_km", 0.0),
        "total_distance_actual_km": totals.get("total_distance_km", 0.0),
        "total_duration_planned_min": totals.get("total_duration_min", 0.0),
        "total_duration_actual_min": totals.get("total_duration_min", 0.0),
        "fuel_cost_planned_inr": fuel,
        "fuel_cost_actual_inr": fuel,
        "co2_emissions_kg": totals.get("total_co2_emissions_kg", 0.0),
        "on_time_pct": totals.get("on_time_pct", 0.0),
        "vehicle_utilization_pct": utilization,
        "cost_per_delivery_inr": round(fuel / shipments, 1) if shipments else 0.0,
        "_source": "today_plan",
    }


def _records_in_range(from_date: str, to_date: str) -> List[Dict[str, Any]]:
    """Return history records (+ today's plan) whose date is within the range."""
    start = _parse_date(from_date)
    end = _parse_date(to_date)
    if start > end:
        raise ValueError("'from' date must be on or before 'to' date.")

    history = data_access.load_route_history()
    today = _today_history_entry()
    if today is not None and not any(h.get("date") == today["date"] for h in history):
        history = history + [today]

    selected = [
        h for h in history
        if h.get("date") and start <= _parse_date(h["date"]) <= end
    ]
    selected.sort(key=lambda h: h["date"])
    return selected


def _avg(values: List[float]) -> float:
    nums = [v for v in values if v is not None]
    return sum(nums) / len(nums) if nums else 0.0


# --- Public API --------------------------------------------------------------

def summary(from_date: str, to_date: str) -> Dict[str, Any]:
    """Aggregated KPI-card data for the selected range."""
    records = _records_in_range(from_date, to_date)
    if not records:
        raise ValueError("No route history found for the selected date range.")

    shipments = sum(r.get("shipments_delivered", 0) for r in records)
    dist_planned = sum(r.get("total_distance_planned_km", 0) for r in records)
    dist_actual = sum(r.get("total_distance_actual_km", 0) for r in records)
    fuel_planned = sum(r.get("fuel_cost_planned_inr", 0) for r in records)
    fuel_actual = sum(r.get("fuel_cost_actual_inr", 0) for r in records)
    co2 = sum(r.get("co2_emissions_kg", 0) for r in records)

    dur_planned = sum(r.get("total_duration_planned_min", 0) for r in records)
    dur_actual = sum(r.get("total_duration_actual_min", 0) for r in records)

    eta_accuracy = {
        "estimated_duration_min": round(dur_planned, 1),
        "actual_duration_min": round(dur_actual, 1),
        "delta_min": round(dur_actual - dur_planned, 1),
        "accuracy_pct": round(
            100.0 - (abs(dur_actual - dur_planned) / dur_planned * 100.0)
            if dur_planned else 0.0,
            1,
        ),
    }

    return {
        "date_range": {"from": from_date, "to": to_date},
        "days": len(records),
        "totals": {
            "shipments_delivered": shipments,
            "on_time_pct": round(_avg([r.get("on_time_pct") for r in records]), 1),
            "total_distance_planned_km": round(dist_planned, 1),
            "total_distance_actual_km": round(dist_actual, 1),
            "total_fuel_cost_planned_inr": round(fuel_planned, 1),
            "total_fuel_cost_actual_inr": round(fuel_actual, 1),
            "total_co2_emissions_kg": round(co2, 1),
            "avg_cost_per_delivery_inr": round(
                fuel_actual / shipments if shipments else 0.0, 1
            ),
            "avg_vehicle_utilization_pct": round(
                _avg([r.get("vehicle_utilization_pct") for r in records]), 1
            ),
        },
        "eta_accuracy": eta_accuracy,
    }


def trends(from_date: str, to_date: str) -> Dict[str, Any]:
    """Daily time-series for the trend charts."""
    records = _records_in_range(from_date, to_date)
    if not records:
        raise ValueError("No route history found for the selected date range.")

    series = [
        {
            "date": r["date"],
            "distance_planned_km": r.get("total_distance_planned_km", 0),
            "distance_actual_km": r.get("total_distance_actual_km", 0),
            "duration_planned_min": r.get("total_duration_planned_min", 0),
            "duration_actual_min": r.get("total_duration_actual_min", 0),
            "fuel_cost_planned_inr": r.get("fuel_cost_planned_inr", 0),
            "fuel_cost_actual_inr": r.get("fuel_cost_actual_inr", 0),
            "on_time_pct": r.get("on_time_pct", 0),
            "vehicle_utilization_pct": r.get("vehicle_utilization_pct", 0),
        }
        for r in records
    ]
    return {"date_range": {"from": from_date, "to": to_date}, "series": series}


def cost_breakdown(from_date: str, to_date: str) -> Dict[str, Any]:
    """Fuel vs labour vs vehicle-wear share of total delivery cost."""
    records = _records_in_range(from_date, to_date)
    if not records:
        raise ValueError("No route history found for the selected date range.")

    cost_model = get_config().get("cost_model", {})
    labour_rate = float(cost_model.get("labour_cost_per_hour_inr", 120))
    wear_rate = float(cost_model.get("vehicle_wear_cost_per_km_inr", 2.5))

    fuel_cost = sum(r.get("fuel_cost_actual_inr", 0) for r in records)
    distance = sum(r.get("total_distance_actual_km", 0) for r in records)

    active_drivers = [d for d in data_access.load_drivers() if d.get("status") == "active"]
    daily_labour_hours = sum(_shift_hours(d.get("shift", "")) for d in active_drivers)
    labour_cost = daily_labour_hours * labour_rate * len(records)
    wear_cost = distance * wear_rate

    total = fuel_cost + labour_cost + wear_cost

    def _pct(part: float) -> float:
        return round(part / total * 100.0, 1) if total else 0.0

    return {
        "date_range": {"from": from_date, "to": to_date},
        "fuel_cost_inr": round(fuel_cost, 1),
        "labour_cost_inr": round(labour_cost, 1),
        "vehicle_wear_cost_inr": round(wear_cost, 1),
        "total_cost_inr": round(total, 1),
        "breakdown": [
            {"category": "Fuel", "value": round(fuel_cost, 1), "pct": _pct(fuel_cost)},
            {"category": "Labour", "value": round(labour_cost, 1), "pct": _pct(labour_cost)},
            {"category": "Vehicle wear", "value": round(wear_cost, 1), "pct": _pct(wear_cost)},
        ],
    }


def weather_correlation() -> Dict[str, Any]:
    """Average delay (actual - planned duration) grouped by weather condition."""
    history = data_access.load_route_history()
    grouped: Dict[str, List[float]] = {}
    for r in history:
        cond = r.get("weather_condition", "unknown")
        delay = r.get("total_duration_actual_min", 0) - r.get("total_duration_planned_min", 0)
        grouped.setdefault(cond, []).append(delay)

    correlation = [
        {
            "weather_condition": cond,
            "avg_delay_min": round(_avg(delays), 1),
            "days": len(delays),
        }
        for cond, delays in sorted(grouped.items())
    ]
    return {"correlation": correlation}


def _build_html_report(
    from_date: str,
    to_date: str,
    totals: Dict[str, Any],
    eta: Dict[str, Any],
    trend_series: List[Dict[str, Any]],
    cost_data: Dict[str, Any],
) -> str:
    """Build a self-contained, responsive HTML email dashboard for the weekly report."""

    on_time = totals["on_time_pct"]
    on_time_color = "#16a34a" if on_time >= 90 else "#d97706" if on_time >= 75 else "#dc2626"

    eta_acc = eta["accuracy_pct"]
    eta_color = "#16a34a" if eta_acc >= 90 else "#d97706" if eta_acc >= 75 else "#dc2626"

    dist_variance = round(
        totals["total_distance_actual_km"] - totals["total_distance_planned_km"], 1
    )
    dist_variance_str = (f"+{dist_variance}" if dist_variance > 0 else str(dist_variance)) + " km"
    dist_var_color = "#dc2626" if dist_variance > 0 else "#16a34a"

    fuel_variance = round(
        totals["total_fuel_cost_actual_inr"] - totals["total_fuel_cost_planned_inr"], 1
    )
    fuel_var_color = "#dc2626" if fuel_variance > 0 else "#16a34a"
    fuel_variance_str = (f"+₹{fuel_variance}" if fuel_variance > 0 else f"₹{fuel_variance}")

    # Build trend rows (last 5 entries)
    trend_rows = ""
    for row in trend_series[-5:]:
        date = row.get("date", "")
        dist_pl = row.get("distance_planned_km", 0)
        dist_ac = row.get("distance_actual_km", 0)
        ot = row.get("on_time_pct", 0)
        fuel_ac = row.get("fuel_cost_actual_inr", 0)
        ot_col = "#16a34a" if ot >= 90 else "#d97706" if ot >= 75 else "#dc2626"
        trend_rows += f"""
        <tr>
          <td style="padding:10px 14px;border-bottom:1px solid #e2e8f0;color:#374151;">{date}</td>
          <td style="padding:10px 14px;border-bottom:1px solid #e2e8f0;color:#374151;text-align:center;">{dist_pl} km</td>
          <td style="padding:10px 14px;border-bottom:1px solid #e2e8f0;color:#374151;text-align:center;">{dist_ac} km</td>
          <td style="padding:10px 14px;border-bottom:1px solid #e2e8f0;text-align:center;">
            <span style="color:{ot_col};font-weight:600;">{ot}%</span>
          </td>
          <td style="padding:10px 14px;border-bottom:1px solid #e2e8f0;color:#374151;text-align:right;">₹{fuel_ac:,.1f}</td>
        </tr>"""

    # Cost breakdown bars
    cost_bars = ""
    for item in cost_data.get("breakdown", []):
        cat = item.get("category", "")
        pct = item.get("pct", 0)
        val = item.get("value", 0)
        color = {"Fuel": "#2563eb", "Labour": "#0d9488", "Vehicle wear": "#d97706"}.get(cat, "#6b7280")
        cost_bars += f"""
        <div style="margin-bottom:14px;">
          <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
            <span style="font-size:13px;color:#374151;font-weight:500;">{cat}</span>
            <span style="font-size:13px;color:#6b7280;">₹{val:,.1f} ({pct}%)</span>
          </div>
          <div style="background:#e2e8f0;border-radius:4px;height:10px;">
            <div style="background:{color};width:{min(pct,100)}%;height:10px;border-radius:4px;"></div>
          </div>
        </div>"""

    generated_at = datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime(
        "%d %b %Y, %I:%M %p IST"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Weekly Route Optimization Report</title>
</head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:'Segoe UI',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:24px 0;">
  <tr><td align="center">
    <table width="640" cellpadding="0" cellspacing="0" style="max-width:640px;width:100%;">

      <!-- HEADER -->
      <tr>
        <td bgcolor="#1e3a5f" style="background-color:#1e3a5f;background:linear-gradient(135deg,#1e3a5f 0%,#2563eb 100%);border-radius:12px 12px 0 0;padding:32px 36px;">
          <div style="display:flex;align-items:center;">
            <div style="width:44px;height:44px;background:rgba(255,255,255,0.2);border-radius:10px;display:inline-block;text-align:center;line-height:44px;font-size:22px;margin-right:14px;">🚛</div>
            <div style="display:inline-block;vertical-align:top;margin-left:14px;">
              <div style="color:#93c5fd;font-size:11px;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;">Warehouse Route Optimizer</div>
              <div style="color:#ffffff;font-size:22px;font-weight:700;margin-top:2px;">Weekly Performance Report</div>
            </div>
          </div>
          <div style="margin-top:16px;color:#bfdbfe;font-size:13px;">
            📅 Period: <strong style="color:#fff;">{from_date}</strong> to <strong style="color:#fff;">{to_date}</strong>
            &nbsp;&nbsp;|&nbsp;&nbsp; Generated: {generated_at}
          </div>
        </td>
      </tr>

      <!-- KPI CARDS -->
      <tr>
        <td style="background:#ffffff;padding:28px 36px 8px;">
          <div style="font-size:12px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:#6b7280;margin-bottom:16px;">Key Performance Indicators</div>
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td width="25%" style="padding:0 8px 16px 0;">
                <div style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:10px;padding:16px;text-align:center;">
                  <div style="font-size:28px;font-weight:700;color:#0369a1;">{totals['shipments_delivered']}</div>
                  <div style="font-size:11px;color:#6b7280;margin-top:4px;font-weight:600;">Shipments Delivered</div>
                </div>
              </td>
              <td width="25%" style="padding:0 8px 16px 0;">
                <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;padding:16px;text-align:center;">
                  <div style="font-size:28px;font-weight:700;color:{on_time_color};">{on_time}%</div>
                  <div style="font-size:11px;color:#6b7280;margin-top:4px;font-weight:600;">On-Time Delivery</div>
                </div>
              </td>
              <td width="25%" style="padding:0 8px 16px 0;">
                <div style="background:#fefce8;border:1px solid #fde68a;border-radius:10px;padding:16px;text-align:center;">
                  <div style="font-size:28px;font-weight:700;color:#92400e;">{totals['avg_vehicle_utilization_pct']}%</div>
                  <div style="font-size:11px;color:#6b7280;margin-top:4px;font-weight:600;">Avg Fleet Utilization</div>
                </div>
              </td>
              <td width="25%" style="padding:0 0 16px 0;">
                <div style="background:#fdf4ff;border:1px solid #e9d5ff;border-radius:10px;padding:16px;text-align:center;">
                  <div style="font-size:28px;font-weight:700;color:#7e22ce;">{eta_acc}%</div>
                  <div style="font-size:11px;color:#6b7280;margin-top:4px;font-weight:600;">ETA Accuracy</div>
                </div>
              </td>
            </tr>
          </table>
        </td>
      </tr>

      <!-- DISTANCE & FUEL ROW -->
      <tr>
        <td style="background:#ffffff;padding:0 36px 24px;">
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td width="50%" style="padding-right:8px;">
                <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:18px;">
                  <div style="font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#6b7280;margin-bottom:12px;">📍 Distance</div>
                  <table width="100%">
                    <tr>
                      <td style="font-size:13px;color:#6b7280;">Planned</td>
                      <td style="font-size:13px;color:#374151;font-weight:600;text-align:right;">{totals['total_distance_planned_km']} km</td>
                    </tr>
                    <tr>
                      <td style="font-size:13px;color:#6b7280;padding-top:6px;">Actual</td>
                      <td style="font-size:13px;color:#374151;font-weight:600;text-align:right;padding-top:6px;">{totals['total_distance_actual_km']} km</td>
                    </tr>
                    <tr>
                      <td style="font-size:13px;color:#6b7280;padding-top:6px;border-top:1px solid #e2e8f0;">Variance</td>
                      <td style="font-size:13px;font-weight:700;color:{dist_var_color};text-align:right;padding-top:6px;border-top:1px solid #e2e8f0;">{dist_variance_str}</td>
                    </tr>
                  </table>
                </div>
              </td>
              <td width="50%" style="padding-left:8px;">
                <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:18px;">
                  <div style="font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#6b7280;margin-bottom:12px;">⛽ Fuel Cost</div>
                  <table width="100%">
                    <tr>
                      <td style="font-size:13px;color:#6b7280;">Planned</td>
                      <td style="font-size:13px;color:#374151;font-weight:600;text-align:right;">₹{totals['total_fuel_cost_planned_inr']:,.1f}</td>
                    </tr>
                    <tr>
                      <td style="font-size:13px;color:#6b7280;padding-top:6px;">Actual</td>
                      <td style="font-size:13px;color:#374151;font-weight:600;text-align:right;padding-top:6px;">₹{totals['total_fuel_cost_actual_inr']:,.1f}</td>
                    </tr>
                    <tr>
                      <td style="font-size:13px;color:#6b7280;padding-top:6px;border-top:1px solid #e2e8f0;">Variance</td>
                      <td style="font-size:13px;font-weight:700;color:{fuel_var_color};text-align:right;padding-top:6px;border-top:1px solid #e2e8f0;">{fuel_variance_str}</td>
                    </tr>
                  </table>
                </div>
              </td>
            </tr>
          </table>
        </td>
      </tr>

      <!-- COST BREAKDOWN -->
      <tr>
        <td style="background:#ffffff;padding:0 36px 24px;">
          <div style="font-size:12px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:#6b7280;margin-bottom:14px;">💰 Cost Breakdown</div>
          {cost_bars}
          <div style="text-align:right;font-size:13px;color:#374151;font-weight:700;margin-top:8px;border-top:1px solid #e2e8f0;padding-top:10px;">
            Total Cost: ₹{cost_data.get('total_cost_inr', 0):,.1f}
          </div>
        </td>
      </tr>

      <!-- DAILY TREND TABLE -->
      <tr>
        <td style="background:#ffffff;padding:0 36px 28px;">
          <div style="font-size:12px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:#6b7280;margin-bottom:14px;">📈 Recent Daily Performance</div>
          <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;border-collapse:collapse;">
            <thead>
              <tr style="background:#f8fafc;">
                <th style="padding:10px 14px;text-align:left;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;color:#6b7280;">Date</th>
                <th style="padding:10px 14px;text-align:center;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;color:#6b7280;">Planned km</th>
                <th style="padding:10px 14px;text-align:center;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;color:#6b7280;">Actual km</th>
                <th style="padding:10px 14px;text-align:center;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;color:#6b7280;">On-Time %</th>
                <th style="padding:10px 14px;text-align:right;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;color:#6b7280;">Fuel Cost</th>
              </tr>
            </thead>
            <tbody>{trend_rows}</tbody>
          </table>
        </td>
      </tr>

      <!-- SUMMARY STATS -->
      <tr>
        <td style="background:#ffffff;padding:0 36px 28px;">
          <div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;padding:18px;">
            <div style="font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#1d4ed8;margin-bottom:10px;">📊 Summary Statistics</div>
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="font-size:13px;color:#374151;padding:4px 0;">Avg Cost per Delivery</td>
                <td style="font-size:13px;color:#1d4ed8;font-weight:700;text-align:right;">₹{totals['avg_cost_per_delivery_inr']}</td>
              </tr>
              <tr>
                <td style="font-size:13px;color:#374151;padding:4px 0;">Total CO₂ Emissions</td>
                <td style="font-size:13px;color:#374151;font-weight:700;text-align:right;">{totals['total_co2_emissions_kg']} kg</td>
              </tr>
              <tr>
                <td style="font-size:13px;color:#374151;padding:4px 0;">ETA Delta</td>
                <td style="font-size:13px;color:{eta_color};font-weight:700;text-align:right;">{eta['delta_min']} min</td>
              </tr>
              <tr>
                <td style="font-size:13px;color:#374151;padding:4px 0;">Days Covered</td>
                <td style="font-size:13px;color:#374151;font-weight:700;text-align:right;">{len(trend_series)} days</td>
              </tr>
            </table>
          </div>
        </td>
      </tr>

      <!-- FOOTER -->
      <tr>
        <td style="background:#1e293b;border-radius:0 0 12px 12px;padding:20px 36px;text-align:center;">
          <div style="color:#94a3b8;font-size:12px;">This report was automatically generated by the <strong style="color:#cbd5e1;">Warehouse Route Optimizer</strong> system.</div>
          <div style="color:#64748b;font-size:11px;margin-top:6px;">Do not reply to this email. For queries contact your dispatch manager.</div>
        </td>
      </tr>

    </table>
  </td></tr>
</table>
</body>
</html>"""


def send_report(from_date: str, to_date: str) -> Dict[str, Any]:
    """Email an HTML KPI dashboard to the dispatch manager via Power Automate."""
    data = summary(from_date, to_date)
    totals = data["totals"]
    eta = data["eta_accuracy"]

    # Fetch supplementary data needed for the HTML template
    try:
        trend_data = trends(from_date, to_date)
        trend_series = trend_data.get("series", [])
    except ValueError:
        trend_series = []

    try:
        cost_data = cost_breakdown(from_date, to_date)
    except ValueError:
        cost_data = {"breakdown": [], "total_cost_inr": 0}

    html_body = _build_html_report(
        from_date=from_date,
        to_date=to_date,
        totals=totals,
        eta=eta,
        trend_series=trend_series,
        cost_data=cost_data,
    )

    manager_email = get_config().get("alerting", {}).get("dispatch_manager_email")
    alert = send_alert_tool(
        alert_type="weekly_report",
        severity="info",
        message=f"Weekly report ({from_date} to {to_date}) generated and sent to dispatch manager.",
        channel=["email", "dashboard"],
        email_to=manager_email,
        email_subject=f"Route Optimization Weekly Report — {from_date} to {to_date}",
        email_body=html_body,
    )
    logger.info("Weekly report (HTML) generated for %s..%s", from_date, to_date)
    return {
        "status": "sent" if alert.get("email_sent") else "queued",
        "message": (
            "Report sent to dispatch manager via Power Automate."
            if alert.get("email_sent")
            else "Report queued on dashboard (Power Automate not configured)."
        ),
        "alert": alert,
    }
