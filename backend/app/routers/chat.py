"""Component 5 — Chat assistant API router.

Exposes:
  POST /api/chat           — run the chat assistant, persist turn, return reply
  GET  /api/chat/history   — return a single session's turns (no cross-session data)
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app import data_access
from app.core_logger import get_logger
from app.agent import chat_assistant_agent

logger = get_logger("chat_router")

router = APIRouter(prefix="/api/chat", tags=["chat"])

_IST = timezone(timedelta(hours=5, minutes=30))


def _now_ist() -> str:
    return datetime.now(_IST).replace(microsecond=0).isoformat()


# --- Request / response models -----------------------------------------------

class ChatRequest(BaseModel):
    message: str
    conversation_id: str
    page_context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    reply: str
    sources_used: List[str] = []
    suggested_follow_ups: List[str] = []


# --- Endpoints ---------------------------------------------------------------

@router.post("", response_model=ChatResponse)
async def post_chat(body: ChatRequest) -> ChatResponse:
    """Run the chat assistant and persist both turns to the session."""
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="message must not be empty.")

    cid = body.conversation_id
    session = data_access.get_session(cid)

    # Update page context if provided
    if body.page_context:
        session["page_context"] = body.page_context

    # Pass only the last 10 turns as context (user + assistant interleaved)
    recent_turns = session.get("turns", [])[-10:]

    # Run the agent
    result = await chat_assistant_agent.chat(
        message=body.message,
        conversation_id=cid,
        page_context=session.get("page_context"),
        recent_turns=recent_turns,
    )

    # Persist user turn
    turns = session.setdefault("turns", [])
    turn_id_base = len(turns)
    turns.append({
        "turn_id": turn_id_base + 1,
        "role": "user",
        "message": body.message,
        "timestamp": _now_ist(),
    })

    # Persist assistant turn
    turns.append({
        "turn_id": turn_id_base + 2,
        "role": "assistant",
        "message": result["reply"],
        "timestamp": _now_ist(),
        "sources_used": result["sources_used"],
        "suggested_follow_ups": result["suggested_follow_ups"],
    })

    data_access.save_session(cid, session)

    logger.info(
        "chat [%s]: sources=%s follow_ups=%d",
        cid, result["sources_used"], len(result["suggested_follow_ups"]),
    )

    return ChatResponse(
        reply=result["reply"],
        sources_used=result["sources_used"],
        suggested_follow_ups=result["suggested_follow_ups"],
    )


@router.get("/history")
def get_history(conversation_id: str = Query(...)) -> Dict[str, Any]:
    """Return only this session's turns — never another session's data."""
    session = data_access.get_session(conversation_id)
    return {
        "conversation_id": conversation_id,
        "started_at": session.get("started_at"),
        "last_active_at": session.get("last_active_at"),
        "page_context": session.get("page_context"),
        "turns": session.get("turns", []),
    }
