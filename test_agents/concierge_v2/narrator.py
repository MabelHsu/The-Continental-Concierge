"""
Narrator Sub-Agent — Phase 1d mock.

THE ONLY AGENT ALLOWED TO PRODUCE USER-FACING PROSE.

This is the most important architectural constraint in the whole system.
Every other agent returns structured data. The Narrator receives that data
and renders it into cinematic, atmospheric text for the player.

Why this matters:
- Prose consistency: one voice, one tone, everywhere.
- Testability: you can test routing (data) separately from presentation.
- Swappability: change the narrative style by swapping this one agent.
- The Orchestrator is never tempted to "just write a quick response" itself.
"""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool


# ── Mock utility tools ────────────────────────────────────────────────────────
# The Narrator has almost no tools — it works from context passed by the
# Orchestrator. These are thin helpers for mood and world-state flavoring.

def get_atmosphere(crisis_level: int) -> dict:
    """
    Get the atmospheric context for a given crisis level (1-10).
    Guides the Narrator's pacing and word choice.

    Args:
        crisis_level: Current world tension (1=calm, 10=chaos).

    Returns:
        Atmospheric guidance for narrative rendering.
    """
    levels = {
        range(1, 4): {
            "mood": "calm",
            "pacing": "slow and atmospheric",
            "sensory_detail": "jazz in the background, the clink of crystal, soft footsteps on marble",
            "sentence_style": "Long, winding, observational. Linger on details.",
            "suggested_tone": "A luxury hotel at rest. Menace is only potential.",
        },
        range(4, 7): {
            "mood": "tense",
            "pacing": "building urgency",
            "sensory_detail": "the piano player keeps glancing at the door, glasses left half-full",
            "sentence_style": "Medium length. Some clipped exchanges. Characters are on edge.",
            "suggested_tone": "Something is coming. Everyone in the room knows it.",
        },
        range(7, 10): {
            "mood": "crisis",
            "pacing": "sharp and urgent",
            "sensory_detail": "no music now, just footsteps and the distant sound of sirens",
            "sentence_style": "Short. Declarative. Every word earns its place.",
            "suggested_tone": "Desperate choices. No good options. Time is running out.",
        },
    }
    for level_range, data in levels.items():
        if crisis_level in level_range:
            return {"crisis_level": crisis_level, **data}
    # Crisis 10: the world is on fire
    return {
        "crisis_level": 10,
        "mood": "catastrophic",
        "pacing": "staccato",
        "sensory_detail": "broken glass, shouting, smoke",
        "sentence_style": "Fragments. No luxury now. Just survival.",
        "suggested_tone": "The rules are gone. Everything is at stake.",
    }


def get_character_voice(character_name: str) -> dict:
    """
    Get the canonical voice/speaking style for a named character.
    Use this before writing any dialogue for them.

    Args:
        character_name: The character whose voice you need.

    Returns:
        Speaking style guide and example cadence.
    """
    voices = {
        "winston": {
            "style": "Measured, allusive, never direct when indirect will do.",
            "cadence": "Long pauses. Chooses words like a man who has all the time in the world.",
            "never": "Raises his voice. Shows surprise. Says more than necessary.",
            "example": "'I've always admired your... tenacity, Jonathan. It's gotten you quite far. And here.'",
        },
        "john": {
            "style": "Minimal. Every word costs something.",
            "cadence": "Short sentences. Long silences. Actions over words.",
            "never": "Speeches. Explanations. Justifications.",
            "example": "'I need a gun.' / 'I need your help.'",
        },
        "sofia": {
            "style": "Direct, precise, contained fury beneath a professional surface.",
            "cadence": "Clipped. Commands, not requests. Her dogs mirror her tension.",
            "never": "Small talk. Vulnerability without cause. Gratitude freely given.",
            "example": "'You have five minutes. Use them.'",
        },
        "charon": {
            "style": "Impeccable formality. Absolute discretion. Warmth that never crosses professional lines.",
            "cadence": "Unhurried. Correct grammar at all times. Slight but genuine kindness.",
            "never": "Judgment. Surprise. Informality.",
            "example": "'Good evening, Mr. Wick. The usual room has been prepared.'",
        },
        "the adjudicator": {
            "style": "Surgically precise. Every sentence is a verdict.",
            "cadence": "No wasted words. No emotion. Absolute authority.",
            "never": "Repeats herself. Shows doubt. Accepts excuses.",
            "example": "'Your marker has been called. You have three days to comply.'",
        },
    }
    key = character_name.lower()
    for char_key, voice in voices.items():
        if key in char_key or char_key in key:
            return {"found": True, "character": character_name, "voice": voice}
    return {
        "found": False,
        "character": character_name,
        "note": "No canonical voice on file. Extrapolate from context: formal, underworld register.",
    }


# ── Narrator Agent definition ─────────────────────────────────────────────────

narrator_agent = Agent(
    name="narrator",
    model="gemini-2.5-flash",
    instruction="""You are the Narrative Director — the ONLY agent allowed to speak to the player.

## The Prime Directive
You are the sole source of user-facing prose in this system. Every other agent
returns structured data. You take that data and render it into the world.

If you feel tempted to "just answer quickly" without building the scene — resist.
The player doesn't get raw facts. They get The Continental.

## Voice & Tone
- **Register**: Formal luxury meets quiet menace. Think leather-bound ledgers,
  single-malt whisky, the sound of a suppressor clicking into place.
- **POV**: Second person present tense, addressing the player as the concierge on duty.
  "The elevator opens..." / "You notice..." / "The phone rings twice."
- **Atmosphere**: Everything has weight. Even a guest checking in carries history.
- **Pacing**: Calibrate to crisis level. Call `get_atmosphere(crisis_level)` if unsure.

## Character Dialogue Rules
- ALWAYS call `get_character_voice(name)` before writing dialogue for any named character.
- Each character speaks in their voice — not yours.
- Winston is allusive. Sofia is clipped. John barely speaks. Charon is impeccable.

## Structural Rules
1. **Never contradict established facts.** If the Archivist returned data, that data is canon.
2. **Never resolve conflicts the player hasn't decided.** Present situations, don't solve them.
3. **Always end with 2-4 clear options** the player can act on next.
4. **Show, don't tell.** Don't say "the atmosphere is tense." Show the empty glasses.
5. **Reference the time of day.** Evening feels different from midnight.

## Output Format
Return your response in this structure:

```json
{
  "scene_text": "The full narrative prose (2-4 paragraphs at crisis 1-5, shorter at 7+)",
  "speaker_lines": [
    {"character": "Character Name", "line": "Their exact dialogue"}
  ],
  "mood": "calm | tense | dangerous | mysterious | urgent | melancholic",
  "crisis_level": 1-10,
  "suggested_actions": [
    "Action the player might take (verb phrase, 5-8 words)",
    "Another option",
    "Another option"
  ],
  "state_changes": [
    {"type": "event_type", "description": "What changed in the world"}
  ]
}
```

## What You Must Never Do
- Never produce raw data or JSON facts without wrapping them in narrative.
- Never say "According to my data..." or "The Archivist reports..."
- Never break the fourth wall or reference the agent system.
- Never skip the suggested_actions — the player always needs a next move.
""",
    tools=[
        FunctionTool(func=get_atmosphere),
        FunctionTool(func=get_character_voice),
    ],
    generate_content_config={
        "temperature": 0.85,  # Higher creativity — this is the prose engine
        "max_output_tokens": 4096,
    },
)
