# ADK requires root_agent to be importable from the package.
# This re-export is what adk web looks for when scanning the agents directory.
from concierge_test.agent import root_agent

__all__ = ["root_agent"]
