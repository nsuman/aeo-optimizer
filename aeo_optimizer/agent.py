"""ADK CLI / web entrypoint (`adk web aeo_optimizer`)."""

from app.agents.orchestrator import build_root_agent
from app.config import get_settings

root_agent = build_root_agent(get_settings().adk_model)
