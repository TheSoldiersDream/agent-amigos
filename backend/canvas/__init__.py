"""
🧠🎨 Agent Amigos Chalk Board - Package Init

A comprehensive visual thinking and creation surface for Agent Amigos.
Supports: Sketch, Diagram, CAD (floor plans), Media, and Text modes.
"""

from .canvas_models import (
    CanvasState, CanvasObject, Layer, DrawMode, ObjectType,
    AgentDrawCommand, AgentCommandResponse,
    ExportRequest, ExportResponse, ExportFormat,
    FloorPlanTemplate, FloorPlanRoom, FlowchartTemplate, FlowchartNode, FlowchartConnection
)
from .canvas_state import state_manager, CanvasStateManager
from .canvas_router import router as canvas_router
from .canvas_controller import (
    canvas_controller,
    CanvasMCPController,
    DrawCommand,
    CommandType,
    CommandResult,
    get_pending_draw_commands,
    execute_draw_command,
    register_mcp_tools
)

__all__ = [
    # Models
    "CanvasState",
    "CanvasObject", 
    "Layer",
    "DrawMode",
    "ObjectType",
    "AgentDrawCommand",
    "AgentCommandResponse",
    "ExportRequest",
    "ExportResponse",
    "ExportFormat",
    "FloorPlanTemplate",
    "FloorPlanRoom",
    "FlowchartTemplate",
    "FlowchartNode",
    "FlowchartConnection",
    # State Management
    "state_manager",
    "CanvasStateManager",
    # Router
    "canvas_router",
    # MCP Controller
    "canvas_controller",
    "CanvasMCPController",
    "DrawCommand",
    "CommandType",
    "CommandResult",
    "get_pending_draw_commands",
    "execute_draw_command",
    "register_mcp_tools",
]
