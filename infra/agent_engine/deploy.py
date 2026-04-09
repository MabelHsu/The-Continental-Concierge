"""
Agent Engine Deployment
========================
Deploys the Continental Concierge orchestrator to
Vertex AI Agent Engine Runtime.

Usage:
    python deploy_agent_engine.py --project PROJECT_ID --region REGION
"""

import argparse
import os

from google.cloud import aiplatform
from vertexai.preview import agent_engines

from app.agents.concierge.agent import root_agent


def deploy(project_id: str, region: str, staging_bucket: str):
    """Deploy the root agent to Vertex AI Agent Engine."""
    
    # Initialize Vertex AI
    aiplatform.init(
        project=project_id,
        location=region,
        staging_bucket=staging_bucket,
    )

    # Package requirements
    requirements = [
        "google-adk>=0.3.0",
        "google-cloud-aiplatform[agent_engines]>=1.75.0",
        "asyncpg>=0.30.0",
        "mcp>=1.0.0",
    ]

    # Environment variables for the deployed agent
    env_vars = {
        "GOOGLE_CLOUD_PROJECT": project_id,
        "GOOGLE_CLOUD_REGION": region,
        "ALLOYDB_HOST": os.environ.get("ALLOYDB_HOST", ""),
        "ALLOYDB_DATABASE": "continental",
        "ALLOYDB_USER": "continental_app",
        # Password sourced from Secret Manager at runtime
    }

    print("Creating Agent Engine app...")
    
    # Create the Agent Engine app with the root agent
    agent_engine = agent_engines.AgentEngine.create(
        agent_engine=root_agent,
        requirements=requirements,
        display_name="continental-concierge",
        description=(
            "The Continental Concierge — a multi-agent narrative system "
            "set in a fictional assassin's hotel. Routes requests through "
            "Archivist, Ledger, Timeline, and Narrator agents."
        ),
        extra_packages=[
            "./app",    # Agent code
            "./mcp",    # MCP server configs
        ],
        env_vars=env_vars,
    )

    print(f"Agent Engine deployed: {agent_engine.resource_name}")
    print(f"Agent Engine ID: {agent_engine.name}")
    
    return agent_engine


def test_agent(agent_engine, test_query: str = "Who is Winston Scott?"):
    """Test the deployed agent with a sample query."""
    print(f"\nTesting with: '{test_query}'")
    
    # Create a session
    session = agent_engine.create_session(
        user_id="test-user-001",
    )
    
    # Send a query
    response = session.send_message(test_query)
    
    print(f"Response: {response}")
    return response


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy Continental Concierge to Agent Engine")
    parser.add_argument("--project", required=True, help="Google Cloud project ID")
    parser.add_argument("--region", default="us-central1", help="Google Cloud region")
    parser.add_argument("--bucket", required=True, help="GCS staging bucket (gs://...)")
    parser.add_argument("--test", action="store_true", help="Run a test query after deployment")
    
    args = parser.parse_args()
    
    agent_engine = deploy(
        project_id=args.project,
        region=args.region,
        staging_bucket=args.bucket,
    )
    
    if args.test:
        test_agent(agent_engine)
