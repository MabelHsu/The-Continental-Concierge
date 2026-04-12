"""
Ledger Tools — Manage the social graph: debts, relationships, reputation.

The Ledger Agent is the only agent that should write to these tables.
Other agents may read through their own tools but should defer mutations here.
"""

from typing import Optional


async def get_debts(
    character_name: Optional[str] = None,
    status: str = "outstanding",
    marker_type: Optional[str] = None,
) -> list[dict]:
    """
    Query debts and markers with optional filters.

    Args:
        character_name: Filter by creditor or debtor name
        status: Filter by status (default: outstanding)
        marker_type: Filter by type (blood_oath, marker, favor, debt, promise, threat)

    Returns:
        List of debts with creditor/debtor names and details.
    """
    pass


async def create_debt(
    creditor_name: str,
    debtor_name: str,
    marker_type: str,
    description: str,
    value: int,
    witness_name: Optional[str] = None,
) -> dict:
    """
    Record a new debt or marker.

    Args:
        creditor_name: Who is owed
        debtor_name: Who owes
        marker_type: Type of obligation
        description: What the debt is for
        value: Severity/importance (1-10)
        witness_name: Optional witness

    Returns:
        The created debt record.
    """
    pass


async def update_debt_status(
    debt_id: int,
    new_status: str,
    notes: Optional[str] = None,
) -> dict:
    """
    Update the status of a debt (called_in, fulfilled, betrayed, etc.).

    Args:
        debt_id: The debt to update
        new_status: New status
        notes: Explanation

    Returns:
        Updated debt and any cascading effects.
    """
    pass


async def get_relationships(character_name: str) -> list[dict]:
    """
    Get all relationships for a character.

    Args:
        character_name: The character to look up

    Returns:
        List of relationships with other characters.
    """
    pass


async def update_relationship(
    character_a: str,
    character_b: str,
    new_type: Optional[str] = None,
    strength_delta: Optional[int] = None,
    notes: Optional[str] = None,
) -> dict:
    """
    Update a relationship between two characters.

    Args:
        character_a: First character
        character_b: Second character
        new_type: New relationship type (optional)
        strength_delta: Change in strength -100 to +100 (optional)
        notes: What caused the change

    Returns:
        Updated relationship.
    """
    pass


async def get_reputation(character_name: str) -> dict:
    """
    Get a character's reputation score and recent changes.

    Args:
        character_name: Character to check

    Returns:
        Reputation score and list of recent changes with causes.
    """
    pass


async def modify_reputation(
    character_name: str,
    delta: int,
    reason: str,
) -> dict:
    """
    Change a character's reputation score.

    Args:
        character_name: Who to modify
        delta: Change amount (-100 to +100)
        reason: Why the change happened

    Returns:
        New reputation score and any threshold effects.
    """
    pass


async def get_faction_standing() -> list[dict]:
    """
    Get current influence standings for all factions.

    Returns:
        Ranked list of factions by influence.
    """
    pass
