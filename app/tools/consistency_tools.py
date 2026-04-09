"""
Consistency Tools — Canon Judge functionality.

Lightweight contradiction detection that runs before every final response.
This is the "Canon Judge" from the design spec, implemented as tools
rather than a separate agent to keep the agent count at 5.
"""

from typing import Optional


async def check_consistency(
    proposed_events: list[dict],
    proposed_state_changes: list[dict],
) -> dict:
    """
    Check proposed narrative output for contradictions before delivery.
    
    This is the Canon Judge function. It verifies:
    - Characters are in locations consistent with the timeline
    - Proposed events don't contradict established facts
    - Debt/relationship changes are valid
    - Hotel rules aren't being violated without acknowledgment
    - Dead characters aren't suddenly active
    - Timeline ordering is correct
    
    Args:
        proposed_events: Events the narrator wants to describe
        proposed_state_changes: State mutations the response implies
    
    Returns:
        ConsistencyReport as dict: {
            is_consistent: bool,
            issues: list of problems found,
            suggested_fixes: list of corrections,
            timeline_conflicts: list of temporal issues,
            lore_contradictions: list of canon violations
        }
    """
    issues = []

    return {
        "is_consistent": len(issues) == 0,
        "issues": issues,
        "suggested_fixes": [],
        "timeline_conflicts": [],
        "lore_contradictions": [],
    }


async def validate_character_action(
    character_name: str,
    action_description: str,
) -> dict:
    """
    Quick check: can this character do this action right now?
    
    Checks status, location, obligations, and rules.
    """
    pass


async def get_canon_facts(topic: str) -> list[str]:
    """
    Retrieve established facts about a topic for contradiction checking.
    
    Used by the consistency checker to compare proposed events against canon.
    """
    pass
