import pytest

# This test relies on the optional MCP runtime dependency.
pytest.importorskip("fastmcp")

from agent_mcp.registrar import MCPRegistrar
from canvas.canvas_controller import canvas_controller


def test_canvas_tools_register_with_registrar():
    registrar = MCPRegistrar()
    tools = canvas_controller.get_mcp_tools()
    assert tools, "Expected canvas controller to provide at least one MCP tool spec"

    # Register tools
    for t in tools:
        registrar.register_tool(t["name"], t)

    registered = registrar.get_registered_tools()
    assert registered, "No tools were registered with the MCP registrar"
    assert tools[0]["name"] in registered
