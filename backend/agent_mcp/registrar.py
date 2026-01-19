"""
MCP Registrar adapter for Agent Amigos canvas integration.

Provides a simple 'register_tool' and 'add_tool' API that wraps tools into AgentTool
instances and forwards them to the local Agent Amigos MCP server (agent_mcp.server.SERVER).
Also keeps a local registry for testing/verification.
"""
from typing import Any, Dict
import logging

from agent_mcp.server import AgentTool, SERVER
from canvas.canvas_controller import canvas_controller

logger = logging.getLogger(__name__)


class MCPRegistrar:
    def __init__(self):
        self._registered = set()

    def register_tool(self, name: str, spec: Dict[str, Any]) -> None:
        """Register a tool spec (name + JSON schema) with the local MCP server."""
        try:
            def _make_fn(_name):
                def _fn(**arguments):
                    return canvas_controller.handle_mcp_tool_call(_name, arguments)
                return _fn

            tool = AgentTool(
                name=name,
                description=spec.get("description"),
                parameters=spec.get("parameters", {"type": "object"}),
                output_schema=None,
                annotations=None,
                serializer=None,
                tags={spec.get("category", "canvas")},
                meta={"category": spec.get("category", "canvas"), "source": "Canvas"},
                fn=_make_fn(name),
            )
            SERVER.add_tool(tool)
            self._registered.add(name)
            logger.info("Registered Canvas MCP tool: %s", name)
        except Exception as e:
            logger.exception("Failed to register canvas tool %s: %s", name, e)

    def add_tool(self, tool_obj: Any) -> None:
        """Forward raw AgentTool-like objects to the MCP server."""
        try:
            SERVER.add_tool(tool_obj)
            self._registered.add(getattr(tool_obj, "name", "<unknown>"))
            logger.info("Added tool to MCP server: %s", getattr(tool_obj, "name", "<unknown>"))
        except Exception:
            logger.exception("Failed to add tool object to MCP server")

    def get_registered_tools(self):
        return set(self._registered)
