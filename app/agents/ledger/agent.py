"""
Ledger Agent — The social graph accountant.

Tracks debts, markers, alliances, reputation, and all inter-character
obligations. Validates changes and detects cascading effects.
"""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from app.shared.config import config
from app.tools.ledger_tools import (
    get_debts,
    create_debt,
    update_debt_status,
    get_relationships,
    update_relationship,
    get_reputation,
    modify_reputation,
    get_faction_standing,
)


LEDGER_INSTRUCTION = open(
    "app/agents/ledger/prompt.md", "r"
).read()

ledger_agent = Agent(
    name="ledger",
    model=config.model_name,
    instruction=LEDGER_INSTRUCTION,
    tools=[
        FunctionTool(func=get_debts),
        FunctionTool(func=create_debt),
        FunctionTool(func=update_debt_status),
        FunctionTool(func=get_relationships),
        FunctionTool(func=update_relationship),
        FunctionTool(func=get_reputation),
        FunctionTool(func=modify_reputation),
        FunctionTool(func=get_faction_standing),
    ],
    generate_content_config={
        "temperature": 0.2,  # Very precise for financial/social accounting
        "max_output_tokens": 2048,
    },
)
