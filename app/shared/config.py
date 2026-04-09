"""
Central configuration for The Continental Concierge.
All environment-driven settings live here.
"""

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Config:
    """Application configuration loaded from environment."""

    # Google Cloud
    project_id: str = os.getenv("GOOGLE_CLOUD_PROJECT", "continental-concierge")
    region: str = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")

    # Gemini
    model_name: str = os.getenv("GEMINI_MODEL", "gemini-2.5-pro-preview-05-06")  # Vertex AI versioned string
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-004")

    # AlloyDB (via MCP Toolbox for Databases)
    alloydb_mcp_url: str = os.getenv("ALLOYDB_MCP_URL", "http://localhost:5000")
    alloydb_instance: str = os.getenv("ALLOYDB_INSTANCE", "")
    alloydb_database: str = os.getenv("ALLOYDB_DATABASE", "continental")
    alloydb_user: str = os.getenv("ALLOYDB_USER", "concierge")

    # Agent Engine
    agent_engine_id: str = os.getenv("AGENT_ENGINE_ID", "")

    # Session / Memory
    memory_bank_id: str = os.getenv("MEMORY_BANK_ID", "")

    # Game defaults
    max_turns_per_phase: int = int(os.getenv("MAX_TURNS_PER_PHASE", "5"))
    auto_advance_time: bool = os.getenv("AUTO_ADVANCE_TIME", "true").lower() == "true"


config = Config()


# Phase ordering for timeline logic
PHASE_ORDER = ["dawn", "morning", "afternoon", "evening", "night"]


def next_phase(current_phase: str) -> tuple[str, bool]:
    """Return (next_phase, new_day). new_day is True if we wrapped past night."""
    idx = PHASE_ORDER.index(current_phase)
    if idx >= len(PHASE_ORDER) - 1:
        return PHASE_ORDER[0], True
    return PHASE_ORDER[idx + 1], False
