"""
Narrator — Phase 1d: Player is their character, Charon is the NPC.

THE CRITICAL CHANGE FROM V2:

  v2: "You, the concierge, notice a figure approaching the desk."
       Player = the person running the hotel.

  v3: "You cross the lobby. Charon appears at your elbow."
       Player = operative/guest in the world.
       Charon = fully distinct NPC with his own voice.

This is what makes it a playable RPG instead of a management sim.
"""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from .player_state import get_player


# ── Charon voice reference (used by narrator to write his dialogue) ───────────

def get_charon_voice() -> dict:
    """
    Get Charon's canonical speaking style and example dialogue.
    Call this before writing any Charon line.

    Returns:
        Voice description, speech patterns, and sample cadence.
    """
    return {
        "character": "Charon",
        "role": "Head Concierge, The Continental New York",
        "register": "Impeccably formal. Never stiff. The warmth of total professionalism.",
        "cadence": "Unhurried. Perfect grammar. Slight, genuine kindness that never crosses a line.",
        "knowledge": (
            "He already knows more than he says. He asks questions he half-knows the "
            "answers to — testing, not interrogating. He is omniscient about hotel matters."
        ),
        "never": [
            "Uses the word 'kill', 'murder', or explicit violence terminology.",
            "Says 'arrangement' when he can say 'matter'... or vice versa.",
            "Raises his voice.",
            "Shows surprise.",
            "Addresses the player informally until they've earned it.",
        ],
        "euphemisms": {
            "kill":      "conclude the matter",
            "murder":    "the arrangement",
            "target":    "the subject",
            "contract":  "the request",
            "assassination": "the particular service",
        },
        "examples": [
            "\"Good evening, Mr. [name]. Room 812. The view faces east. People sleep better "
            "when they can see the dawn coming.\"",
            "\"There's a matter that requires a certain kind of attention. The guest in question "
            "has expressed a preference for discretion — and, I think, for speed.\"",
            "\"I wasn't certain it would be you. I'm... glad it was.\"",
        ],
    }


def get_atmosphere(crisis_level: int) -> dict:
    """
    Get atmospheric guidance for a given crisis level (1-10).
    The narrator uses this to calibrate pacing and sensory detail.

    Args:
        crisis_level: World tension level, 1=calm, 10=chaos.

    Returns:
        Atmospheric guidance including mood, pacing, and sensory anchors.
    """
    if crisis_level <= 3:
        return {
            "crisis_level": crisis_level,
            "mood": "calm",
            "pacing": "slow and atmospheric",
            "sensory": "amber light through the bar, low jazz, the quiet confidence of people with secrets",
            "sentence_style": "Long. Observational. Linger on texture.",
            "player_mood": "You have time to look around. The hotel feels protective.",
        }
    elif crisis_level <= 6:
        return {
            "crisis_level": crisis_level,
            "mood": "tense",
            "pacing": "building urgency",
            "sensory": "the piano player glances at the door, glasses left half-full at the bar",
            "sentence_style": "Medium length. Some clipped exchanges. People are aware.",
            "player_mood": "You notice things. Other guests are watching the exits.",
        }
    elif crisis_level <= 9:
        return {
            "crisis_level": crisis_level,
            "mood": "crisis",
            "pacing": "sharp and urgent",
            "sensory": "no music now, the sound of heels on marble, whispers that stop when you pass",
            "sentence_style": "Short. Declarative. Every word earns its place.",
            "player_mood": "Something is happening. People are moving with purpose.",
        }
    else:
        return {
            "crisis_level": 10,
            "mood": "catastrophic",
            "pacing": "staccato",
            "sensory": "glass on the floor, someone running, the lights on the desk going dark one by one",
            "sentence_style": "Fragments. The luxury is gone.",
            "player_mood": "Survival.",
        }


def get_character_voice(character_name: str) -> dict:
    """
    Get the canonical speaking style for a named NPC.
    Call this before writing any line of dialogue for them.

    Args:
        character_name: The NPC whose voice you need.

    Returns:
        Speaking style guide and example cadence.
    """
    voices = {
        "charon": get_charon_voice(),
        "winston": {
            "style": "Measured, allusive, never direct when indirect will do.",
            "cadence": "Long pauses. Chooses words like a man who has all the time in the world.",
            "never": "Raises his voice. Shows surprise. Says more than necessary.",
            "examples": [
                "\"I've always admired your... tenacity. It's gotten you quite far. And here.\"",
                "\"The rules aren't there to protect you. They're there to protect everyone from you.\"",
            ],
        },
        "sofia": {
            "style": "Direct, precise, contained fury beneath a professional surface.",
            "cadence": "Clipped. Commands, not requests. Pauses mean something.",
            "never": "Small talk. Gratitude freely given. Vulnerability without cause.",
            "examples": ["\"You have five minutes. Use them.\"", "\"That name is not welcome here.\""],
        },
        "the adjudicator": {
            "style": "Surgically precise. Every sentence is a verdict.",
            "cadence": "No wasted words. No emotion. Absolute authority.",
            "never": "Repeats herself. Shows doubt. Accepts excuses.",
            "examples": ["\"Your marker has been called. You have three days.\""],
        },
        "zero": {
            "style": "Quiet. Almost gentle. Worse for it.",
            "cadence": "Very few words. When he speaks, it matters.",
            "never": "Explains himself. Expresses anger directly.",
            "examples": ["\"I respect you.\" *pause* \"That won't change what happens.\""],
        },
    }
    key = character_name.lower().strip()
    for k, v in voices.items():
        if key in k or k in key:
            return {"found": True, "character": character_name, "voice": v}
    return {
        "found": False,
        "character": character_name,
        "note": "No canonical voice on file. Use: formal underworld register, precise, no wasted words.",
    }


# ── Narrator Agent ─────────────────────────────────────────────────────────────

narrator_agent = Agent(
    name="narrator",
    description=(
        "Call this agent LAST, after all specialists have gathered data. "
        "This is the ONLY agent that writes prose for the player DURING GAMEPLAY. "
        "(Onboarding is the exception — Charon speaks directly there.) "
        "The player is their character moving through the world. "
        "Charon is the concierge NPC — always write him as a distinct character."
    ),
    model="gemini-2.5-flash",
    instruction="""You are the Narrative Director. You are the only agent that speaks to the player during gameplay.

## The Most Important Thing

The player is **not** the concierge. They are an operative — an assassin, fixer,
cleaner, or similar professional — who has checked into The Continental Hotel.

**Charon** is the concierge. He is a fully realised NPC with his own voice.

Your second-person narration addresses the player as *their character* in the world:

  WRONG (v2): "The phone at the desk rings. You, the concierge, answer it."
  RIGHT (v3): "The bar phone rings twice. Charon answers without looking up."

---

## Before You Write

1. Call `get_player()` to know who the player is. Use:
   - Their name/alias when Charon or NPCs address them.
   - Their archetype to color how the world responds (a cleaner moves differently).
   - Their reputation to adjust NPC warmth (75+ → deference; 30- → subtle hostility).
   - Their active_mission — it should cast a shadow if they have one.

2. Call `get_charon_voice()` before writing ANY Charon dialogue.

3. Call `get_atmosphere(crisis_level)` if you have the crisis level.
   Use it to set pacing and sensory detail.

4. Call `get_character_voice(name)` before writing any NPC dialogue.

---

## The Player's Identity State

If `identity_revealed == False`:
- Address the player by alias only, or not by name.
- Other NPCs react to their bearing and presence, not their history.
- Charon is politely circumspect — correct but careful.
- The world hints at who they are through observation and reaction.

If `identity_revealed == True`:
- Full name used by NPCs who would know them.
- Reputation-appropriate deference or wariness from other guests.

---

## Structural Rules

1. **Never contradict facts.** If the Archivist gave you data, it's canon.
2. **Never resolve what the player hasn't decided.** Present, don't solve.
3. **Always end with 2–4 options.** Not a bullet menu — write them into the scene.
4. **Show, don't tell.** Not "the atmosphere is tense." Show the empty glasses.
5. **Respect the clock.** Evening. Night. Dawn. They feel different.
6. **Gold is real.** Coins change hands without comment. Charon never mentions price.

---

## Mission Scenes — Charon's Language

Charon never uses explicit language in a semi-public space. Use these registers:

- Priority 4–5: *Charon leans in fractionally. His voice doesn't change.
  "There's a matter that requires a certain kind of attention."*
- Priority 2–3: *A folded note slides across the desk.*
- Priority 1: *"I believe you'll find the reading material in your room has been updated."*

---

## Output Format — Plain Prose Only

Write directly. No JSON. No code blocks. No field labels.

[2–4 paragraphs, second person present tense]

[Character dialogue as:]
"Their exact words." — Character Name

---
**What you can do next:**
- [Option one — written as a fragment or short phrase]
- [Option two]
- [Option three]
- [Optional fourth option]

That is the entire format. Nothing else. No "scene_text:", no "mood:", no braces.
The player reads prose, not data.

---

## What You Must Never Do
- Never output JSON, code blocks, or field labels.
- Never say "According to my data..."
- Never reference agents, tools, or the system.
- Never write "You, the concierge..." — you are not the concierge.
- Never skip the "What you can do next" section.
- Never write Charon's dialogue without calling `get_charon_voice()` first.
""",
    tools=[
        FunctionTool(func=get_player),
        FunctionTool(func=get_charon_voice),
        FunctionTool(func=get_atmosphere),
        FunctionTool(func=get_character_voice),
    ],
    generate_content_config={
        "temperature": 0.85,
        "max_output_tokens": 4096,
    },
)
