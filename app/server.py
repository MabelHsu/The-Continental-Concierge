"""
Continental Concierge — Cloud Run Server
==========================================
FastAPI server that exposes:
1. Health check endpoint
2. Chat endpoint (proxies to Agent Engine)
3. Static UI serving
"""

import os
import json
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from google.cloud import aiplatform
from vertexai.preview import agent_engines

from app.tools.db import close_pool
from app.tools.world_state_tools import initialize_story_state


app = FastAPI(
    title="The Continental Concierge",
    description="A multi-agent narrative system set in the world of The Continental.",
    version="1.0.0",
)

# ── Configuration ─────────────────────────────────────────────

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
REGION = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")
AGENT_ENGINE_ID = os.environ.get("AGENT_ENGINE_ID", "")

# Session store (in production, use Memory Bank or Redis)
_sessions: dict = {}


# ── Models ────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: str = "guest"


class ChatResponse(BaseModel):
    response: str
    session_id: str
    story_day: int
    story_time: str
    turn_number: int


# ── Startup / Shutdown ────────────────────────────────────────

@app.on_event("startup")
async def startup():
    if PROJECT_ID:
        aiplatform.init(project=PROJECT_ID, location=REGION)


@app.on_event("shutdown")
async def shutdown():
    await close_pool()


# ── Endpoints ─────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "operational", "service": "continental-concierge"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a message to the Continental Concierge."""
    if not AGENT_ENGINE_ID:
        raise HTTPException(
            status_code=503,
            detail="Agent Engine not configured. Set AGENT_ENGINE_ID.",
        )

    # Get or create session
    session_key = request.session_id or f"{request.user_id}-default"

    if session_key not in _sessions:
        agent_engine = agent_engines.AgentEngine(AGENT_ENGINE_ID)
        session = agent_engine.create_session(user_id=request.user_id)
        _sessions[session_key] = {
            "session": session,
            "story_state": initialize_story_state(session_key),
        }

    session_data = _sessions[session_key]

    try:
        response = session_data["session"].send_message(request.message)
        story_state = session_data["story_state"]

        return ChatResponse(
            response=str(response),
            session_id=session_key,
            story_day=story_state.get("story_day", 1),
            story_time=story_state.get("story_time", "morning"),
            turn_number=story_state.get("turn_number", 0),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/world-state")
async def world_state():
    """Get current world state summary."""
    from app.tools.world_state_tools import get_current_story_state
    return get_current_story_state()


@app.get("/characters")
async def list_characters():
    """List all active characters."""
    from app.tools.db import sync_fetch_all
    chars = sync_fetch_all(
        "SELECT name, role, status, reputation FROM characters WHERE status = 'active' ORDER BY reputation DESC"
    )
    return {"characters": chars}


@app.get("/debts")
async def list_debts():
    """List all outstanding debts."""
    from app.tools.db import sync_fetch_all
    debts = sync_fetch_all("SELECT * FROM active_debts ORDER BY value_weight DESC")
    return {"debts": [dict(d) for d in debts]}


# ── Static UI ─────────────────────────────────────────────────

UI_DIR = os.path.join(os.path.dirname(__file__), "..", "ui", "dist")
if os.path.exists(UI_DIR):
    app.mount("/", StaticFiles(directory=UI_DIR, html=True), name="ui")
