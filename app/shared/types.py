"""
Shared data types used across agents.
Agents return structured outputs, not prose.
The Narrative Director is the only agent that produces user-facing text.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class TaskType(str, Enum):
    LORE_LOOKUP = "lore_lookup"
    CHARACTER_QUERY = "character_query"
    DEBT_CHECK = "debt_check"
    DEBT_MODIFY = "debt_modify"
    TIMELINE_QUERY = "timeline_query"
    TIMELINE_CHECK = "timeline_check"
    EVENT_LOG = "event_log"
    MISSION_CREATE = "mission_create"
    MISSION_UPDATE = "mission_update"
    RULE_CHECK = "rule_check"
    NARRATE = "narrate"
    CONSISTENCY_CHECK = "consistency_check"


@dataclass
class Task:
    """A unit of work assigned by the orchestrator to a specialist."""
    task_type: TaskType
    description: str
    parameters: dict = field(default_factory=dict)
    priority: int = 3  # 1=low, 5=critical
    source_agent: str = "concierge"


@dataclass
class AgentResult:
    """Structured output from a specialist agent."""
    agent: str
    task_type: TaskType
    success: bool
    data: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)
    narration_hints: list[str] = field(default_factory=list)


@dataclass
class WorldSnapshot:
    """Current state of the world, passed to the narrative director."""
    day: int
    phase: str
    crisis_level: int
    crisis_name: str
    hotel_status: str
    active_characters: list[dict] = field(default_factory=list)
    pending_missions: list[dict] = field(default_factory=list)
    recent_events: list[dict] = field(default_factory=list)
    active_debts: list[dict] = field(default_factory=list)
    pending_violations: list[dict] = field(default_factory=list)


@dataclass
class ConsistencyReport:
    """Output of the consistency checker before final response."""
    is_consistent: bool
    issues: list[str] = field(default_factory=list)
    suggested_fixes: list[str] = field(default_factory=list)
    timeline_conflicts: list[str] = field(default_factory=list)
    lore_contradictions: list[str] = field(default_factory=list)


@dataclass
class NarrativeOutput:
    """Final output from the narrative director."""
    scene_text: str
    speaker_lines: list[dict] = field(default_factory=list)  # [{character, line}]
    mood: str = "neutral"
    tension_delta: int = 0  # -3 to +3
    suggested_next_actions: list[str] = field(default_factory=list)
    state_changes: list[dict] = field(default_factory=list)
