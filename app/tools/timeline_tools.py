"""
Timeline Tools — Spatial and temporal tracking.

Manages character locations, event logging, and collision detection.
"""

from typing import Optional


async def get_current_locations() -> list[dict]:
    """
    Get a map of all locations and who is currently there.
    
    Returns:
        List of locations with characters_present arrays.
    """
    pass


async def move_character(
    character_name: str,
    destination: str,
    reason: Optional[str] = None,
) -> dict:
    """
    Move a character to a new location.
    
    Args:
        character_name: Who to move
        destination: Location name
        reason: Why they're moving
    
    Returns:
        Updated location and any collisions detected.
    """
    pass


async def log_event(
    event_type: str,
    title: str,
    description: str,
    location: Optional[str] = None,
    severity: int = 3,
    participants: Optional[list[dict]] = None,
    is_public: bool = True,
) -> dict:
    """
    Record a new event in the timeline.
    
    Args:
        event_type: Type of event
        title: Short title
        description: Full description
        location: Where it happened
        severity: 1-10
        participants: List of {name, role} dicts
        is_public: Whether other characters would know about it
    
    Returns:
        The created event.
    """
    pass


async def get_timeline(
    day_from: Optional[int] = None,
    day_to: Optional[int] = None,
    location: Optional[str] = None,
    limit: int = 20,
) -> list[dict]:
    """
    Get events from the timeline with optional filters.
    """
    pass


async def detect_collisions() -> list[dict]:
    """
    Scan for timeline/spatial conflicts.
    
    Checks for:
    - Hostile characters in the same Continental location
    - Expired mission deadlines
    - Characters in two places at once (data error)
    - Unresolved violations
    
    Returns:
        List of collision objects with type, details, and severity.
    """
    pass


async def get_upcoming_deadlines(within_phases: int = 3) -> list[dict]:
    """
    Get missions with deadlines approaching within N phases.
    """
    pass


async def check_character_availability(character_name: str) -> dict:
    """
    Check if a character is available for interaction.
    
    Returns:
        Availability status, current location, and any conflicting obligations.
    """
    pass
