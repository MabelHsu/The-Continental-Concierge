"""
Continental Concierge — Cloud Run Server
==========================================
FastAPI server that exposes:
  1. Health check
  2. /chat — main gameplay loop (proxies to Agent Engine)
  3. /player — read player state
  4. /player/missions — available missions for this player
  5. /world-state — current story state
  6. /characters — active NPC roster
  7. /debts — outstanding debts (for debugging / UI)
  8. Static UI serving

Session lifecycle:
  - On first /chat: create Agent Engine session + player record
  - On subsequent /chat: look up existing session, inject player context
  - If player.onboarding_complete == False: Agent Engine routes to onboarding_agent
"""

import logging
import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from google.cloud import aiplatform
from vertexai.preview import agent_engines

from app.tools.db import close_pool, fetch_all
from app.tools.player_tools import (
    get_player,
    create_player_character,
    get_available_missions,
    get_inventory,
)
from app.tools.world_state_tools import get_world_state

logger = logging.getLogger(__name__)


app = FastAPI(
    title="The Continental Concierge",
    description=(
        "A multi-agent narrative RPG set in the world of The Continental. "
        "You are an operative. The hotel is real. The rules are binding."
    ),
    version="2.0.0",
)


# ── Configuration ─────────────────────────────────────────────────────────────

PROJECT_ID      = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
# GOOGLE_CLOUD_LOCATION matches the Vertex AI standard env var name and the
# value documented in .env.template. (Fallback to GOOGLE_CLOUD_REGION kept
# as a transitional alias so a stale shell doesn't break bring-up.)
LOCATION        = os.environ.get("GOOGLE_CLOUD_LOCATION") \
                   or os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")
AGENT_ENGINE_ID = os.environ.get("AGENT_ENGINE_ID", "")

# In-memory session registry: session_key → {agent_session, turn_count}
# Player state is always read from AlloyDB, not from this dict.
_sessions: dict = {}


# ── Request / Response Models ─────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: str = "guest"


class ChatResponse(BaseModel):
    response: str
    session_id: str
    story_day: int
    story_phase: str
    crisis_level: int
    turn_number: int
    # Player snapshot — lets the UI render the HUD without a second call
    player: Optional[dict] = None
    onboarding_complete: bool = True


class PlayerResponse(BaseModel):
    player: Optional[dict]
    onboarding_complete: bool
    message: str = ""


class MissionsResponse(BaseModel):
    missions: list[dict]
    player_reputation: int


# ── Startup / Shutdown ────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    if PROJECT_ID:
        aiplatform.init(project=PROJECT_ID, location=LOCATION)
    logger.info("Continental Concierge server started (location=%s).", LOCATION)


@app.on_event("shutdown")
async def shutdown():
    await close_pool()
    logger.info("Continental Concierge server shutdown.")


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Liveness probe."""
    return {
        "status": "operational",
        "service": "continental-concierge",
        "version": "2.0.0",
    }


# ── Chat — Main Gameplay Loop ─────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a player message to the Continental Concierge system.

    First message in a new session triggers:
      1. Agent Engine session creation
      2. Player character row creation (pending onboarding)
      3. Onboarding Agent takes over until check-in is complete

    Subsequent messages route through the full Concierge orchestration loop.
    Player context is injected automatically — the orchestrator reads it from AlloyDB.
    """
    if not AGENT_ENGINE_ID:
        raise HTTPException(
            status_code=503,
            detail="Agent Engine not configured. Set AGENT_ENGINE_ID environment variable.",
        )

    session_key = request.session_id or f"{request.user_id}-default"

    # ── New session bootstrap ─────────────────────────────────────────────────
    if session_key not in _sessions:
        agent_engine = agent_engines.AgentEngine(AGENT_ENGINE_ID)
        agent_session = agent_engine.create_session(user_id=request.user_id)

        # Create the player row (path defaults to 'pending' until first Charon exchange)
        await create_player_character(
            session_id=session_key,
            user_id=request.user_id,
            creation_path="pending",
        )

        _sessions[session_key] = {
            "session": agent_session,
            "turn_count": 0,
        }
        logger.info("New session created: %s", session_key)

    session_data = _sessions[session_key]

    # ── Inject session_id into message context ────────────────────────────────
    # The Agent Engine session carries this via user_id, but we also
    # prepend it as a system hint so the orchestrator can call get_player().
    enriched_message = f"[session_id:{session_key}] {request.message}"

    try:
        response = session_data["session"].send_message(enriched_message)
        session_data["turn_count"] += 1

        # Read world state and player state for response metadata
        world = await get_world_state() or {}
        player = await get_player(session_key)

        return ChatResponse(
            response=str(response),
            session_id=session_key,
            story_day=world.get("day", 1),
            story_phase=world.get("phase", "evening"),
            crisis_level=world.get("crisis_level", 1),
            turn_number=session_data["turn_count"],
            player=player,
            onboarding_complete=player.get("onboarding_complete", False) if player else False,
        )

    except Exception as e:
        logger.exception("Chat error for session %s", session_key)
        raise HTTPException(status_code=500, detail=str(e))


# ── Player Endpoints ──────────────────────────────────────────────────────────

@app.get("/player/{session_id}", response_model=PlayerResponse)
async def get_player_state(session_id: str):
    """
    Get the current player character state for a session.
    Returns None player if onboarding hasn't started.
    """
    player = await get_player(session_id)
    if not player:
        return PlayerResponse(
            player=None,
            onboarding_complete=False,
            message="No character found for this session. Start a chat to begin.",
        )
    return PlayerResponse(
        player=player,
        onboarding_complete=player.get("onboarding_complete", False),
    )


@app.get("/player/{session_id}/missions", response_model=MissionsResponse)
async def get_player_missions(
    session_id: str,
    limit: int = Query(default=3, ge=1, le=10),
):
    """
    Get missions currently available to this player.
    Filtered by reputation gate. Maximum 3 by default — Charon is discreet.
    """
    player = await get_player(session_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found.")
    if not player.get("onboarding_complete"):
        raise HTTPException(status_code=400, detail="Player has not completed check-in.")

    missions = await get_available_missions(session_id, limit=limit)
    return MissionsResponse(
        missions=missions,
        player_reputation=player.get("reputation", 50),
    )


@app.get("/player/{session_id}/inventory")
async def get_player_inventory(session_id: str):
    """Get the player's current inventory."""
    player = await get_player(session_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found.")
    inventory = await get_inventory(session_id)
    return {
        "inventory": inventory,
        "gold_coins": player.get("gold_coins", 0),
    }


# ── World State ───────────────────────────────────────────────────────────────

@app.get("/world-state")
async def world_state():
    """Current story state: day, phase, crisis level, hotel status."""
    return await get_world_state()


# ── NPC Roster ────────────────────────────────────────────────────────────────

@app.get("/characters")
async def list_characters(status: str = Query(default="active")):
    """
    List characters currently in the world.
    Filter by status: active | injured | hiding | excommunicado | dead

    The JSONB containment check `NOT (traits @> '["player"]'::jsonb)` uses
    the GIN index on `characters(traits)` and is the correct way to exclude
    player-tagged rows — `traits::text[]` is not a valid cast.
    """
    chars = await fetch_all(
        """
        SELECT c.name, c.alias, c.title, c.status, c.reputation,
               f.name AS faction, l.name AS location
        FROM characters c
        LEFT JOIN factions f ON f.id = c.faction_id
        LEFT JOIN locations l ON l.id = c.current_location_id
        WHERE c.status = $1
          AND NOT (c.traits @> '["player"]'::jsonb)
        ORDER BY c.reputation DESC
        """,
        status,
    )
    return {"characters": chars, "count": len(chars)}


# ── Debts Ledger ──────────────────────────────────────────────────────────────

@app.get("/debts")
async def list_debts(status: str = Query(default="outstanding")):
    """List debts and markers, defaulting to outstanding."""
    debts = await fetch_all(
        """
        SELECT dm.id, dm.marker_type, dm.description, dm.value, dm.status,
               cr.name AS creditor, db.name AS debtor
        FROM debts_markers dm
        JOIN characters cr ON cr.id = dm.creditor_id
        JOIN characters db ON db.id = dm.debtor_id
        WHERE dm.status = $1
        ORDER BY dm.value DESC, dm.created_day ASC
        """,
        status,
    )
    return {"debts": debts, "count": len(debts)}


# ── Active Violations ─────────────────────────────────────────────────────────

@app.get("/violations")
async def list_violations():
    """List pending rule violations."""
    violations = await fetch_all(
        """
        SELECT rv.id, rv.day, rv.phase, rv.severity, rv.adjudication,
               hr.title AS rule, c.name AS violator
        FROM rule_violations rv
        JOIN hotel_rules hr ON hr.id = rv.rule_id
        JOIN characters c ON c.id = rv.violator_id
        WHERE rv.adjudication = 'pending'
        ORDER BY rv.day DESC
        """
    )
    return {"violations": violations, "count": len(violations)}


# ── Static UI ─────────────────────────────────────────────────────────────────
# Serves the single-file demo UI at / (ui/index.html). Mounted LAST so every
# explicit API route above takes precedence. With `html=True`, unmatched paths
# fall through to index.html — fine because the UI is a single document.
# The legacy ui/dist/ path is checked first so a future React build can drop in
# without a code change.

_UI_CANDIDATES = [
    os.path.join(os.path.dirname(__file__), "..", "ui", "dist"),
    os.path.join(os.path.dirname(__file__), "..", "ui"),
]
for _ui_path in _UI_CANDIDATES:
    if os.path.exists(os.path.join(_ui_path, "index.html")):
        app.mount("/", StaticFiles(directory=_ui_path, html=True), name="ui")
        logger.info("Mounted UI from %s", _ui_path)
        break
