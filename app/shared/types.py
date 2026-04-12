"""
Shared data types used across agents.
Agents return structured outputs, not prose.
The Narrative Director is the only agent that produces user-facing text.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


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
    MISSION_OFFER = "mission_offer"  # Charon offers available work to the player
    MISSION_COMPLETE = "mission_complete"  # Player resolves their active mission
    RULE_CHECK = "rule_check"
    NARRATE = "narrate"
    CONSISTENCY_CHECK = "consistency_check"
    # ── Player system ──────────────────────────────────────────────────────
    ONBOARDING = "onboarding"  # Identity creation / revelation flow
    PLAYER_QUERY = "player_query"  # Read current player state
    PLAYER_STAT_CHANGE = "player_stat_change"  # Reputation / gold / location mutations
    INVENTORY_UPDATE = "inventory_update"  # Add / remove inventory items


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


# ── Player types ───────────────────────────────────────────────────────────────


@dataclass
class PlayerCharacter:
    """
    The player's character as it exists in the world.
    Read from player_status_view after onboarding completes.
    """

    session_id: str
    user_id: str
    name: Optional[str]
    alias: Optional[str]
    title: Optional[str]
    archetype: Optional[str]
    backstory: Optional[str]

    # Stats
    reputation: int = 50
    combat_rating: int = 50
    influence: int = 30
    gold_coins: int = 7

    # World position
    faction_name: Optional[str] = None
    current_location: Optional[str] = None
    is_continental: bool = False
    status: str = "active"

    # Mission
    active_mission_title: Optional[str] = None
    active_mission_type: Optional[str] = None
    mission_deadline_day: Optional[int] = None
    missions_completed: int = 0
    missions_failed: int = 0

    # Inventory & standings
    inventory: list[dict] = field(default_factory=list)
    faction_standings: list[dict] = field(default_factory=list)

    # Flags
    onboarding_complete: bool = False
    identity_revealed: bool = False

    @classmethod
    def from_db(cls, row: dict) -> "PlayerCharacter":
        """Build from a player_status_view row."""
        return cls(**{k: v for k, v in row.items() if k in cls.__dataclass_fields__})

    def display_name(self) -> str:
        """Best available name: real name > alias > 'Unknown Operative'."""
        return self.name or self.alias or "Unknown Operative"

    def to_context_dict(self) -> dict[str, Any]:
        """Compact context dict passed to every agent call."""
        return {
            "name": self.display_name(),
            "archetype": self.archetype,
            "reputation": self.reputation,
            "gold_coins": self.gold_coins,
            "faction": self.faction_name,
            "location": self.current_location,
            "is_on_consecrated_ground": self.is_continental,
            "active_mission": self.active_mission_title,
            "status": self.status,
            "identity_revealed": self.identity_revealed,
        }


@dataclass
class OnboardingState:
    """
    Tracks where the player is in the character creation / revelation flow.
    Passed to the Onboarding Agent at the start of each onboarding turn.
    """

    session_id: str
    creation_path: str  # 'pending' | 'mystery' | 'custom'
    current_step: int  # 0 = not started
    is_complete: bool = False

    # Mystery path
    identity_clues: list[dict] = field(default_factory=list)
    identity_revealed: bool = False

    # Collected data so far
    collected: dict = field(default_factory=dict)  # {name, alias, archetype, ...}

    # Step definitions per path
    MYSTERY_STEPS: int = 5
    CUSTOM_STEPS: int = 4

    def next_step(self) -> int:
        return self.current_step + 1

    def steps_remaining(self) -> int:
        total = self.MYSTERY_STEPS if self.creation_path == "mystery" else self.CUSTOM_STEPS
        return max(0, total - self.current_step)

    def is_path_chosen(self) -> bool:
        return self.creation_path in ("mystery", "custom")


@dataclass
class MissionOffer:
    """
    A mission Charon is presenting to the player.
    Narrator uses this to write Charon's pitch scene.
    """

    mission_id: int
    title: str
    mission_type: str
    description: str
    priority: int
    requested_by: Optional[str]
    requester_faction: Optional[str]
    deadline_day: Optional[int]
    deadline_phase: Optional[str]
    # What the player stands to gain / risk — set by orchestrator
    reward_hint: str = ""
    risk_level: int = 3  # 1=low, 5=extreme
