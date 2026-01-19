"""
Canvas Agent Integration

Registers the Canvas as a team agent and hooks it into the AgentCoordinator.
This module wires canvas controller events to the coordinator, marks the agent
online, and adds simple event logging for agent interactions.
"""

from typing import Optional
import logging

from tools.agent_coordinator import (
    agent_online,
    agent_idle,
    agent_working,
    agent_thinking,
    set_agent_tool,
)

from .canvas_controller import canvas_controller

logger = logging.getLogger(__name__)


def _command_listener(cmd):
    """Listener called on queued commands: mark agent thinking/working."""
    try:
        # Mark the canvas agent thinking when we receive a command
        agent_thinking("canvas", f"Queued: {cmd.command_type}")
        # When added to queue, mark working briefly
        agent_working("canvas", f"Executing: {cmd.command_type}")
    except Exception as e:
        logger.debug("Canvas listener error: %s", e)


def init_canvas_agent(register_with_mcp: Optional[object] = None):
    """
    Initialize the Canvas agent with coordinator.

    Optionally register MCP tools: pass an MCP server-like object with `register_tool`.
    """
    try:
        # Mark canvas online and set a default tool
        agent_online("canvas")
        set_agent_tool("canvas", "canvas", "🎨")

        # Register listener to watch queued draw commands and report via coordinator
        canvas_controller.add_listener(_command_listener)

        # If an MCP server is passed, register the canvas tools there too
        if register_with_mcp is not None and hasattr(canvas_controller, "get_mcp_tools"):
            try:
                tools = canvas_controller.get_mcp_tools()
                for t in tools:
                    register_with_mcp.register_tool(t["name"], t)
            except Exception as e:
                logger.warning("Failed to register canvas tools with MCP: %s", e)

        logger.info("Canvas agent initialized and online")
    except Exception as e:
        logger.exception("Failed to init Canvas agent: %s", e)


def shutdown_canvas_agent():
    """Shutdown hook to clear listeners or mark idle."""
    try:
        canvas_controller.listeners.clear()
        agent_idle("canvas")
    except Exception:
        pass
