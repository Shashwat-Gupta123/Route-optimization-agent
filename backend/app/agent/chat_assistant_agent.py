"""Chat assistant agent (Component 5).

Loads its system prompt, guardrails, and tool allowlist from
``backend/app/prompts/chat_assistant.yaml`` at startup — never from a Python
string literal — so the prompt is reviewable without touching application logic.

The agent is strictly read-only: only the seven tools in the YAML allowlist are
registered. Mutation tools (optimize_routes, send_alert, etc.) are deliberately
excluded.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from app import config
from app.core_logger import get_logger

logger = get_logger("chat_assistant")

_IST = timezone(timedelta(hours=5, minutes=30))
_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
_YAML_PATH = _PROMPTS_DIR / "chat_assistant.yaml"

# Cached YAML config
_prompt_config: Optional[Dict[str, Any]] = None


def _load_prompt_config() -> Dict[str, Any]:
    global _prompt_config  # noqa: PLW0603
    if _prompt_config is None:
        with _yaml_PATH.open("r", encoding="utf-8") as fh:
            _prompt_config = yaml.safe_load(fh)
        logger.info(
            "Loaded chat_assistant.yaml v%s (updated %s)",
            _prompt_config.get("version"),
            _prompt_config.get("last_updated"),
        )
    return _prompt_config


# Fix the path reference (use the correct var)
def _get_yaml() -> Dict[str, Any]:
    global _prompt_config  # noqa: PLW0603
    if _prompt_config is None:
        with _YAML_PATH.open("r", encoding="utf-8") as fh:
            _prompt_config = yaml.safe_load(fh)
        logger.info(
            "Loaded chat_assistant.yaml v%s (updated %s)",
            _prompt_config.get("version"),
            _prompt_config.get("last_updated"),
        )
    return _prompt_config


def _now_ist() -> str:
    return datetime.now(_IST).replace(microsecond=0).isoformat()


def _build_agent():
    """Build the read-only MAF chat assistant agent, or return None if unconfigured."""
    if not (config.AZURE_OPENAI_ENDPOINT and config.AZURE_OPENAI_API_KEY and config.AZURE_OPENAI_DEPLOYMENT):
        logger.warning("Azure OpenAI env vars missing; chat assistant LLM disabled.")
        return None
    try:
        from agent_framework import Agent
        from agent_framework.openai import OpenAIChatCompletionClient

        # Import the 7 read-only tools
        from app.agent.tools.query_shipments import query_shipments_tool
        from app.agent.tools.query_fleet import query_fleet_tool
        from app.agent.tools.query_route_plan import query_route_plan_tool
        from app.agent.tools.query_alerts import query_alerts_tool
        from app.agent.tools.explain_plan import explain_plan_tool
        from app.agent.tools.compute_kpi import compute_kpi_tool
        from app.agent.tools.weather import get_weather_tool

        yaml_cfg = _get_yaml()
        system_prompt = yaml_cfg.get("system_prompt", "You are a warehouse operations assistant.")

        client = OpenAIChatCompletionClient(
            model=config.AZURE_OPENAI_DEPLOYMENT,
            api_key=config.AZURE_OPENAI_API_KEY,
            azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
            api_version=config.AZURE_OPENAI_API_VERSION,
        )
        agent = Agent(
            client=client,
            instructions=system_prompt,
            name="chat_assistant_agent",
            tools=[
                query_shipments_tool,
                query_fleet_tool,
                query_route_plan_tool,
                query_alerts_tool,
                explain_plan_tool,
                compute_kpi_tool,
                get_weather_tool,
            ],
        )
        logger.info(
            "chat_assistant_agent initialized (deployment=%s, yaml_version=%s)",
            config.AZURE_OPENAI_DEPLOYMENT,
            yaml_cfg.get("version"),
        )
        return agent
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to initialize chat_assistant_agent: %s", exc, exc_info=True)
        return None


# Singleton — built once per process
_agent = None


def _get_agent():
    global _agent  # noqa: PLW0603
    if _agent is None:
        _agent = _build_agent()
    return _agent


def _turns_to_messages(turns: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Convert stored turns into the message format the agent expects."""
    messages = []
    for t in turns:
        role = t.get("role", "user")
        msg = t.get("message", "")
        if role in ("user", "assistant") and msg:
            messages.append({"role": role, "content": msg})
    return messages


async def chat(
    message: str,
    conversation_id: str,
    page_context: Optional[Dict[str, Any]] = None,
    recent_turns: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Run the chat assistant agent and return a structured reply.

    Args:
        message:         The user's free-text question.
        conversation_id: UUID identifying the session (for logging only here;
                         persistence is handled by the router).
        page_context:    Optional dict e.g. ``{"page": "planner", "plan_id": "..."}``
                         injected into the prompt for context-sensitive answers.
        recent_turns:    Last 6–10 turns from the session (user + assistant messages).

    Returns:
        ``{ "reply": str, "sources_used": [str], "suggested_follow_ups": [str] }``
    """
    agent = _get_agent()
    yaml_cfg = _get_yaml()

    if agent is None:
        no_data = yaml_cfg.get("response_templates", {}).get(
            "no_data_response",
            "The AI assistant is not configured. Set Azure OpenAI credentials in backend/.env.",
        )
        return {
            "reply": no_data,
            "sources_used": [],
            "suggested_follow_ups": [],
        }

    # Build context prefix from page_context and recent conversation
    context_parts: List[str] = []
    if page_context:
        context_parts.append(f"[Page context: {json.dumps(page_context)}]")
    if recent_turns:
        history_msgs = _turns_to_messages(recent_turns[-10:])
        if history_msgs:
            history_text = "\n".join(
                f"{m['role'].upper()}: {m['content']}" for m in history_msgs
            )
            context_parts.append(f"[Recent conversation:\n{history_text}\n]")

    full_prompt = "\n\n".join(context_parts + [f"USER QUESTION: {message}"])

    try:
        result = await agent.run(full_prompt)
        reply_text = result.text or ""

        # Extract tool names from message contents (MAF AgentResponse API)
        # Tool-call messages have content[i].name = the function name called.
        sources_used: List[str] = []
        for msg in getattr(result, "messages", []):
            for content in getattr(msg, "contents", []) or []:
                name = getattr(content, "name", None)
                # A non-None name on a content item = a tool call was made
                if name and name not in sources_used:
                    sources_used.append(name)

        # Guard: log warning if the reply sounds factual but no tools were called
        if not sources_used and any(
            kw in message.lower()
            for kw in ("how many", "what is", "what are", "which", "count", "total", "cost", "percentage", "how much")
        ):
            logger.warning(
                "chat [%s]: factual question answered with no tool calls — review for hallucination. Q=%r",
                conversation_id,
                message,
            )

        # Extract suggested follow-ups (look for them after a divider in the reply)
        suggested: List[str] = []
        if "follow" in reply_text.lower() or "?" in reply_text:
            # Parse out bullet-point questions from the end of the reply
            lines = reply_text.splitlines()
            for line in reversed(lines):
                stripped = line.strip().lstrip("-•*123456789. ")
                if stripped.endswith("?") and len(stripped) > 10:
                    suggested.insert(0, stripped)
                if len(suggested) >= 3:
                    break

        return {
            "reply": reply_text,
            "sources_used": sources_used,
            "suggested_follow_ups": suggested,
        }

    except Exception as exc:  # noqa: BLE001
        logger.error("chat_assistant_agent.chat failed: %s", exc, exc_info=True)
        return {
            "reply": f"Sorry, I encountered an error processing your question: {exc}",
            "sources_used": [],
            "suggested_follow_ups": [],
        }
