"""Alerting tool.

``send_alert_tool`` is the single place through which every real-time alert in
Component 2 (ETA deviations, breakdowns, urgent orders, store-notification
emails and analytics digests) is emitted. It does two things:

1. **Dashboard** — always appends a structured alert record to ``alerts.json``
   (via the data-access layer) so the UI's alerts panel can show it).
2. **Email** — if ``"email"`` is one of the requested channels, triggers an
   email via SMTP using configured environment variables.

Demo/offline behaviour: if SMTP credentials are not configured, the email
step is skipped gracefully (the dashboard alert is still written) so the
feature works end-to-end without the flow configured.
"""

from __future__ import annotations

import requests
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from app.config import get_config, get_env
from app.core_logger import get_tool_logger
from app import data_access

logger = get_tool_logger("send_alert")

_IST = timezone(timedelta(hours=5, minutes=30))
_HTTP_TIMEOUT = 15  # seconds


def _now_ist_iso() -> str:
    return datetime.now(_IST).replace(microsecond=0).isoformat()


def _send_email_smtp(
    subject: str,
    body: str,
    to_addr: str,
) -> bool:
    """Send email via SMTP."""
    alerting_config = get_config().get("alerting", {})
    
    host_var = alerting_config.get("smtp_host_env_var", "SMTP_HOST")
    port_var = alerting_config.get("smtp_port_env_var", "SMTP_PORT")
    user_var = alerting_config.get("smtp_user_env_var", "SMTP_USER")
    pass_var = alerting_config.get("smtp_password_env_var", "SMTP_PASS")
    from_var = alerting_config.get("email_from_env_var", "SMTP_USER")
    
    smtp_host = get_env(host_var)
    smtp_port = get_env(port_var)
    smtp_user = get_env(user_var)
    smtp_pass = get_env(pass_var)
    email_from = get_env(from_var) or smtp_user
    
    if not smtp_host or not smtp_user or not smtp_pass:
        logger.info("SMTP credentials not fully configured; skipping email send.")
        return False

    try:
        import smtplib
        from email.message import EmailMessage

        msg = EmailMessage()
        if "<html" in body.lower() or "<!doctype html" in body.lower() or "<div" in body.lower():
            msg.set_content(body, subtype='html')
        else:
            msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = email_from
        msg['To'] = to_addr
        
        port = int(smtp_port) if smtp_port else 587
        
        with smtplib.SMTP(smtp_host, port, timeout=_HTTP_TIMEOUT) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
            
        logger.info("Email sent successfully via SMTP to %s", to_addr)
        return True
    except Exception as exc:
        logger.error("Failed to send email via SMTP: %s", exc, exc_info=True)
        return False


def send_alert_tool(
    alert_type: str,
    severity: str,
    message: str,
    channel: Optional[List[str]] = None,
    vehicle_id: Optional[str] = None,
    shipment_id: Optional[str] = None,
    email_to: Optional[str] = None,
    email_subject: Optional[str] = None,
    email_body: Optional[str] = None,
) -> Dict[str, Any]:
    """Record an alert to ``alerts.json`` and optionally email it via Power Automate.

    Args:
        alert_type: Machine-readable category, e.g. ``eta_deviation``,
            ``vehicle_breakdown``, ``urgent_order``, ``store_notified``,
            ``weekly_report``.
        severity: ``info`` | ``warning`` | ``critical``.
        message: Human-readable alert text (also used as the email body).
        channel: Subset of ``["email", "dashboard"]``. Defaults to
            ``["dashboard"]``. Email is only attempted when ``"email"`` is present.
        vehicle_id: Optional related vehicle id.
        shipment_id: Optional related shipment id.
        email_to: Recipient override; defaults to the dispatch-manager address in
            ``config.json``'s ``alerting`` section.
        email_subject: Optional subject line; a sensible default is derived from
            the severity and type when omitted.
        email_body: HTML or plain-text body sent to Power Automate. Falls back
            to ``message`` when omitted.

    Returns:
        The persisted alert dict, augmented with an ``email_sent`` boolean.
    """
    channels = channel or ["dashboard"]
    alerting = get_config().get("alerting", {})

    alert = {
        "alert_id": data_access.next_alert_id(),
        "type": alert_type,
        "severity": severity,
        "vehicle_id": vehicle_id,
        "shipment_id": shipment_id,
        "message": message,
        "created_at": _now_ist_iso(),
        "channel": channels,
        "acknowledged": False,
    }
    data_access.append_alert(alert)

    email_sent = False
    if "email" in channels:
        recipient = email_to or alerting.get("dispatch_manager_email")
        subject = email_subject or f"[{severity.upper()}] Route Optimizer: {alert_type}"
        if recipient:
            email_sent = _send_email_smtp(
                subject=subject,
                body=email_body or message,
                to_addr=recipient,
            )

    logger.info(
        "Alert %s emitted (type=%s severity=%s channels=%s email_sent=%s)",
        alert["alert_id"],
        alert_type,
        severity,
        channels,
        email_sent,
    )
    result = dict(alert)
    result["email_sent"] = email_sent
    return result
