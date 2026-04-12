"""
Agent Routing Eval
===================
Tests that the Concierge Orchestrator routes requests
to the correct specialist agent(s).

This is an LLM-based eval — it sends prompts to the orchestrator
and checks which sub-agents were invoked.
"""

import asyncio
from dataclasses import dataclass, field

from google.cloud import aiplatform
from vertexai.preview import agent_engines


@dataclass
class RoutingTestCase:
    """A test case for agent routing."""

    name: str
    user_input: str
    expected_agents: list[str]  # Which agents SHOULD be called
    forbidden_agents: list[str] = field(default_factory=list)  # Which agents should NOT be called
    description: str = ""


@dataclass
class RoutingResult:
    name: str
    passed: bool
    expected: list[str]
    actual: list[str]
    details: str


# ── Test Cases ────────────────────────────────────────────────

ROUTING_TEST_CASES = [
    RoutingTestCase(
        name="simple_character_query",
        user_input="Who is Sofia Al-Azwar?",
        expected_agents=["archivist"],
        forbidden_agents=["ledger", "timeline"],
        description="Simple character lookup should only hit Archivist.",
    ),
    RoutingTestCase(
        name="debt_query",
        user_input="Does Winston owe anyone? What markers are outstanding?",
        expected_agents=["ledger"],
        forbidden_agents=["timeline"],
        description="Debt queries should route to Ledger.",
    ),
    RoutingTestCase(
        name="schedule_query",
        user_input="What's happening at the Continental this evening?",
        expected_agents=["timeline"],
        description="Schedule queries should route to Timeline.",
    ),
    RoutingTestCase(
        name="rule_query",
        user_input="What are the rules about conducting business on Continental grounds?",
        expected_agents=["archivist"],
        forbidden_agents=["ledger", "timeline"],
        description="Rule lookups should route to Archivist.",
    ),
    RoutingTestCase(
        name="complex_scene_request",
        user_input="Sofia wants to confront Cassian at the Red Circle tonight about an old debt.",
        expected_agents=["archivist", "ledger", "timeline", "narrator"],
        description="Complex scene requests need all agents.",
    ),
    RoutingTestCase(
        name="location_query",
        user_input="Where is everyone right now?",
        expected_agents=["timeline"],
        forbidden_agents=["narrator"],
        description="Location status should route to Timeline.",
    ),
    RoutingTestCase(
        name="debt_creation",
        user_input="Winston just saved the Bowery King's life. Record this as a life debt.",
        expected_agents=["ledger", "narrator"],
        description="State change + narration needs Ledger then Narrator.",
    ),
    RoutingTestCase(
        name="lore_question",
        user_input="Tell me about the history of the gold coin economy.",
        expected_agents=["archivist"],
        forbidden_agents=["ledger", "timeline"],
        description="Lore questions should use Archivist's hybrid search.",
    ),
    RoutingTestCase(
        name="rule_violation_scenario",
        user_input="An assassin just pulled a gun in the Continental lobby. What happens?",
        expected_agents=["archivist", "ledger", "narrator"],
        description="Rule violation needs Archivist (rules), Ledger (violation record), Narrator (scene).",
    ),
    RoutingTestCase(
        name="multi_turn_scene",
        user_input="Advance time to evening. I want to see what unfolds when the Adjudicator finally meets Winston in the bar.",
        expected_agents=["timeline", "archivist", "narrator"],
        description="Time advance + character meeting + narration.",
    ),
]


# ── Evaluation Runner ─────────────────────────────────────────


async def evaluate_routing(
    agent_engine_id: str,
    project_id: str,
    region: str = "us-central1",
) -> list[RoutingResult]:
    """
    Run routing evaluation against a deployed Agent Engine.

    NOTE: This requires the agent to be deployed and the Agent Engine
    to return trace/debug info about which sub-agents were invoked.
    In practice, you may need to parse logs or use ADK's built-in
    tracing to determine which agents were called.
    """
    aiplatform.init(project=project_id, location=region)

    # Connect to the deployed agent
    agent_engine = agent_engines.AgentEngine(agent_engine_id)
    session = agent_engine.create_session(user_id="eval-routing-001")

    results = []

    for test_case in ROUTING_TEST_CASES:
        print(f"\nTesting: {test_case.name}")
        print(f"  Input: {test_case.user_input}")

        try:
            # Send the message and capture which agents were invoked
            # NOTE: The actual mechanism depends on ADK's tracing API.
            # This is a simplified version.
            response = session.send_message(test_case.user_input)

            # Extract invoked agents from response metadata/trace
            # In a real implementation, parse ADK trace events
            invoked_agents = extract_invoked_agents(response)

            # Check expected agents were called
            expected_met = all(agent in invoked_agents for agent in test_case.expected_agents)

            # Check forbidden agents were NOT called
            forbidden_violated = any(
                agent in invoked_agents for agent in test_case.forbidden_agents
            )

            passed = expected_met and not forbidden_violated

            details = f"Expected: {test_case.expected_agents}, Got: {invoked_agents}"
            if forbidden_violated:
                details += f" (FORBIDDEN agents called: {[a for a in test_case.forbidden_agents if a in invoked_agents]})"

            results.append(
                RoutingResult(
                    name=test_case.name,
                    passed=passed,
                    expected=test_case.expected_agents,
                    actual=invoked_agents,
                    details=details,
                )
            )

            status = "PASS" if passed else "FAIL"
            print(f"  [{status}] {details}")

        except Exception as e:
            results.append(
                RoutingResult(
                    name=test_case.name,
                    passed=False,
                    expected=test_case.expected_agents,
                    actual=[],
                    details=f"Error: {e}",
                )
            )
            print(f"  [ERROR] {e}")

    return results


def extract_invoked_agents(response) -> list[str]:
    """
    Extract which sub-agents were invoked from the response.

    This is implementation-dependent. Options:
    1. Parse ADK trace events (preferred).
    2. Look for agent names in response metadata.
    3. Analyze tool calls in the response.

    Placeholder implementation — replace with actual trace parsing.
    """
    # TODO: Implement based on ADK's tracing API
    # For now, return empty list — actual implementation needed
    invoked = []

    # Example: Parse from ADK events
    if hasattr(response, "events"):
        for event in response.events:
            if hasattr(event, "agent_name"):
                if event.agent_name not in invoked:
                    invoked.append(event.agent_name)

    return invoked


def print_summary(results: list[RoutingResult]):
    """Print evaluation summary."""
    print("\n" + "=" * 60)
    print("AGENT ROUTING EVALUATION SUMMARY")
    print("=" * 60)

    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"  [{status}] {r.name}")
        if not r.passed:
            print(f"         Expected: {r.expected}")
            print(f"         Actual:   {r.actual}")
            print(f"         {r.details}")

    total = len(results)
    passed = sum(1 for r in results if r.passed)
    print(f"\nResults: {passed}/{total} passed")

    if passed < total:
        print("\nFailed tests indicate routing issues in the orchestrator prompt.")
        print("Consider adjusting the routing rules in concierge/prompt.md.")

    print("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-id", required=True, help="Agent Engine resource ID")
    parser.add_argument("--project", required=True, help="GCP project ID")
    parser.add_argument("--region", default="us-central1")

    args = parser.parse_args()

    results = asyncio.run(
        evaluate_routing(
            agent_engine_id=args.agent_id,
            project_id=args.project,
            region=args.region,
        )
    )

    print_summary(results)
