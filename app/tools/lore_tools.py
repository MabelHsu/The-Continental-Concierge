"""
Lore Tools — Retrieve world-building information and character data.

Uses both structured queries and semantic search via AlloyDB's hybrid
retrieval capabilities.
"""

from typing import Optional


async def lookup_character(name: str) -> dict:
    """
    Get the full dossier for a character by name or alias.
    
    Args:
        name: Character name or alias (case-insensitive partial match)
    
    Returns:
        Character dossier including faction, location, traits, backstory,
        and recent events involving them.
    """
    # SELECT * FROM v_character_dossier WHERE name ILIKE '%{name}%' OR alias ILIKE '%{name}%'
    # Plus: recent events from event_participants
    # Plus: active debts from debts_markers
    pass


async def lookup_rule(query: str) -> dict:
    """
    Find hotel rules by number or keyword.
    
    Args:
        query: Rule number (e.g., "1") or keyword (e.g., "weapons", "neutral ground")
    
    Returns:
        Matching rules with full text, penalty, and exceptions.
    """
    # If query is numeric: WHERE rule_number = {query}
    # Else: WHERE title ILIKE '%{query}%' OR description ILIKE '%{query}%'
    pass


async def search_lore(query: str, category: Optional[str] = None, limit: int = 5) -> list[dict]:
    """
    Semantic + keyword hybrid search over world lore.
    
    Uses AlloyDB's vector search combined with tag matching for best results.
    Useful for fuzzy queries like "what do we know about the Casablanca incident"
    or "traditions around markers."
    
    Args:
        query: Natural language search query
        category: Optional filter (history, rule, tradition, etc.)
        limit: Max results
    
    Returns:
        Ranked list of lore chunks with relevance scores.
    """
    # 1. Generate embedding for query using text-embedding-004
    # 2. Call search_lore() function in AlloyDB
    # 3. Optionally filter by category
    # 4. Return ranked results
    pass


async def get_character_history(name: str, limit: int = 10) -> list[dict]:
    """
    Get the event history for a specific character.
    
    Args:
        name: Character name
        limit: Max events to return
    
    Returns:
        Chronological list of events involving this character.
    """
    # JOIN events with event_participants on character_id
    pass


async def search_scenes(query: str, day_from: Optional[int] = None, day_to: Optional[int] = None) -> list[dict]:
    """
    Search past scene memories by semantic similarity.
    
    Args:
        query: What you're looking for
        day_from: Start of day range (inclusive)
        day_to: End of day range (inclusive)
    
    Returns:
        Ranked list of scene memories.
    """
    # 1. Generate embedding
    # 2. Call search_scenes() function in AlloyDB
    pass
