"""Microsoft Agent Framework (MAF) route-planner agent.

Creates a single MAF :class:`~agent_framework.Agent` backed by the Azure OpenAI
deployment (connection established exactly like ``test_files/test_endpoints.py``,
using the ``AZURE_OPEN_AI_*`` variables from ``backend/.env``). The three
domain tools — matrix, weather and the OR-Tools solver — are registered with the
agent so it can reason about them, and the same tool functions are called
directly by the deterministic planning pipeline in :mod:`app.agent.service`.

The agent is used for natural-language work: summarising trade-offs between the
generated plans (``/api/plan-routes``) and answering follow-up questions
(``/api/ask``). If Azure credentials are absent the factory returns ``None`` and
the API degrades gracefully (route planning still works; LLM text is skipped).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List, Optional

from app import config
from app.core_logger import get_logger
from app.agent.tools.route_matrix import get_route_matrix_tool
from app.agent.tools.weather import get_weather_tool
from app.agent.tools.optimize_routes import optimize_routes_tool
from app.agent.tools.detect_eta_deviation import detect_eta_deviation_tool
from app.agent.tools.reoptimize_remaining import reoptimize_remaining_tool
from app.agent.tools.send_alert import send_alert_tool

logger = get_logger("agent")

SYSTEM_PROMPT = (
    "You are the Warehouse Route Planner assistant for a dispatch manager. "
    "Given today's shipments and available fleet, you help produce optimized "
    "delivery route plans (fastest, cheapest, balanced) and clearly explain the "
    "trade-offs between them in plain, non-technical language. When asked about a "
    "specific plan, reason using the provided plan data (distances, ETAs, fuel "
    "cost, emissions, effectiveness score). Be concise and practical."
)


@lru_cache(maxsize=1)
def get_agent() -> Optional[Any]:
    """Build (once) and return the MAF agent, or ``None`` if unconfigured."""
    if not (config.AZURE_OPENAI_ENDPOINT and config.AZURE_OPENAI_API_KEY and config.AZURE_OPENAI_DEPLOYMENT):
        logger.warning("Azure OpenAI env vars missing; agent LLM features disabled.")
        return None
    try:
        from agent_framework import Agent
        from agent_framework.openai import OpenAIChatCompletionClient

        client = OpenAIChatCompletionClient(
            model=config.AZURE_OPENAI_DEPLOYMENT,
            api_key=config.AZURE_OPENAI_API_KEY,
            azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
            api_version=config.AZURE_OPENAI_API_VERSION,
        )
        agent = Agent(
            client=client,
            instructions=SYSTEM_PROMPT,
            name="route_planner_agent",
            tools=[
                get_route_matrix_tool,
                get_weather_tool,
                optimize_routes_tool,
                detect_eta_deviation_tool,
                reoptimize_remaining_tool,
                send_alert_tool,
            ],
        )
        logger.info("route_planner_agent initialized (deployment=%s)", config.AZURE_OPENAI_DEPLOYMENT)
        return agent
    except Exception as exc:  # noqa: BLE001 - never let agent init break the API
        logger.error("Failed to initialize MAF agent: %s", exc, exc_info=True)
        return None


def _plans_brief(plans: List[Dict[str, Any]]) -> str:
    """Compact text summary of plan totals for use as LLM context."""
    lines = []
    for p in plans:
        t = p["totals"]
        lines.append(
            f"- {p['plan_name']}: {t['total_distance_km']} km, "
            f"{t['total_duration_min']} min, ₹{t['total_fuel_cost_inr']} fuel, "
            f"{t['total_co2_emissions_kg']} kg CO2, "
            f"score {p['effectiveness_score']}/10, "
            f"{len(p['routes'])} vehicle(s)"
        )
    return "\n".join(lines)


async def summarize_plans(plans: List[Dict[str, Any]]) -> Optional[str]:
    """Ask the agent for a short trade-off summary of the generated plans."""
    agent = get_agent()
    if agent is None or not plans:
        return None
    prompt = (
        "Here are today's three route plans:\n"
        f"{_plans_brief(plans)}\n\n"
        "In 2-3 short sentences, summarise the trade-offs and note which plan you "
        "would recommend and why. Do not use tools."
    )
    try:
        result = await agent.run(prompt)
        return result.text
    except Exception as exc:  # noqa: BLE001
        logger.error("summarize_plans failed: %s", exc, exc_info=True)
        return None


async def answer_question(question: str, plan: Optional[Dict[str, Any]]) -> str:
    """Answer a free-text question about a plan using the agent."""
    agent = get_agent()
    if agent is None:
        return "The AI assistant is not configured. Set the Azure OpenAI credentials in backend/.env to enable it."
    context = ""
    if plan:
        import json

        context = (
            "Use the following route plan as context (JSON):\n"
            f"{json.dumps(plan, ensure_ascii=False)}\n\n"
        )
    try:
        result = await agent.run(f"{context}Question: {question}\nDo not use tools; answer from the context.")
        return result.text
    except Exception as exc:  # noqa: BLE001
        logger.error("answer_question failed: %s", exc, exc_info=True)
        return f"Sorry, I couldn't answer that right now: {exc}"
