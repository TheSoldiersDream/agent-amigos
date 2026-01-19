"""
🧠🎨 Agent Amigos Chalk Board - MCP Controller
Model Context Protocol integration for agent-driven drawing commands.
"""

import json
import asyncio
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CommandType(str, Enum):
    """Types of drawing commands the agent can issue."""
    # Drawing primitives
    DRAW_LINE = "draw_line"
    DRAW_RECTANGLE = "draw_rectangle"
    DRAW_ELLIPSE = "draw_ellipse"
    DRAW_ARROW = "draw_arrow"
    DRAW_PATH = "draw_path"
    DRAW_TEXT = "draw_text"
    DRAW_IMAGE = "draw_image"
    
    # CAD specific
    DRAW_WALL = "draw_wall"
    DRAW_DOOR = "draw_door"
    DRAW_WINDOW = "draw_window"
    DRAW_DIMENSION = "draw_dimension"
    
    # Complex commands
    GENERATE_FLOOR_PLAN = "generate_floor_plan"
    GENERATE_FLOWCHART = "generate_flowchart"
    RENDER_POEM = "render_poem"
    
    # Canvas operations
    CLEAR_CANVAS = "clear_canvas"
    CLEAR_LAYER = "clear_layer"
    SET_MODE = "set_mode"
    SET_ZOOM = "set_zoom"
    PAN_TO = "pan_to"
    
    # Layer operations
    ADD_LAYER = "add_layer"
    REMOVE_LAYER = "remove_layer"
    SET_ACTIVE_LAYER = "set_active_layer"
    TOGGLE_LAYER_VISIBILITY = "toggle_layer_visibility"
    
    # Session operations
    EXPORT_CANVAS = "export_canvas"
    SAVE_SESSION = "save_session"
    LOAD_SESSION = "load_session"


@dataclass
class DrawCommand:
    """A single drawing command from the agent."""
    command_type: CommandType
    parameters: Dict[str, Any]
    thought: Optional[str] = None
    layer_id: Optional[str] = None
    priority: int = 0
    id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "command_type": self.command_type.value,
            "parameters": self.parameters,
            "thought": self.thought,
            "layer_id": self.layer_id,
            "priority": self.priority
        }


@dataclass
class CommandResult:
    """Result of executing a draw command."""
    success: bool
    command_id: str
    message: str = ""
    created_objects: List[str] = field(default_factory=list)
    data: Optional[Dict[str, Any]] = None


class CanvasMCPController:
    """
    MCP Controller for the Canvas component.
    
    This controller serves as the bridge between AI agents and the 
    Canvas drawing canvas. It provides:
    
    1. Command parsing - Converts natural language or structured prompts to draw commands
    2. Command queuing - Manages a queue of pending commands
    3. Execution callbacks - Interfaces with the frontend canvas
    4. State synchronization - Keeps agent state in sync with canvas state
    """
    
    def __init__(self):
        self.command_queue: List[DrawCommand] = []
        self.executed_commands: List[CommandResult] = []
        self.current_session_id: Optional[str] = None
        self.listeners: List[Callable] = []
        self.is_processing = False
        self._command_counter = 0
        
    def add_listener(self, callback: Callable[[DrawCommand], None]):
        """Add a listener for new commands."""
        self.listeners.append(callback)
        
    def remove_listener(self, callback: Callable):
        """Remove a command listener."""
        if callback in self.listeners:
            self.listeners.remove(callback)
            
    def _generate_command_id(self) -> str:
        """Generate unique command ID."""
        self._command_counter += 1
        return f"cmd_{self._command_counter}"
        
    def _notify_listeners(self, command: DrawCommand):
        """Notify all listeners of a new command."""
        for listener in self.listeners:
            try:
                listener(command)
            except Exception as e:
                logger.error(f"Listener error: {e}")
                
    # === Command Creation Methods ===
    
    def create_draw_command(
        self,
        command_type: CommandType,
        parameters: Dict[str, Any],
        thought: Optional[str] = None,
        layer_id: Optional[str] = None,
        priority: int = 0
    ) -> DrawCommand:
        """Create a new draw command."""
        cmd = DrawCommand(
            command_type=command_type,
            parameters=parameters,
            thought=thought,
            layer_id=layer_id,
            priority=priority,
            id=self._generate_command_id()
        )
        return cmd
        
    def queue_command(self, command: DrawCommand) -> str:
        """Add command to queue and notify listeners."""
        self.command_queue.append(command)
        # Sort by priority (higher first)
        self.command_queue.sort(key=lambda c: -c.priority)
        self._notify_listeners(command)
        logger.info(f"Queued command: {command.command_type.value}")
        return command.id
        
    def get_pending_commands(self) -> List[Dict[str, Any]]:
        """Get all pending commands as dicts."""
        return [cmd.to_dict() for cmd in self.command_queue]
        
    def pop_next_command(self) -> Optional[DrawCommand]:
        """Get and remove the next command from queue."""
        if self.command_queue:
            return self.command_queue.pop(0)
        return None
        
    def clear_queue(self):
        """Clear all pending commands."""
        self.command_queue.clear()
        
    def record_result(self, result: CommandResult):
        """Record the result of an executed command."""
        self.executed_commands.append(result)
        if len(self.executed_commands) > 100:  # Keep last 100
            self.executed_commands = self.executed_commands[-100:]
            
    # === High-Level Command Methods ===
    
    def draw_line(
        self,
        x1: float, y1: float, x2: float, y2: float,
        color: str = "#000000",
        width: float = 2,
        thought: Optional[str] = None,
        layer_id: Optional[str] = None
    ) -> str:
        """Queue a line drawing command."""
        cmd = self.create_draw_command(
            CommandType.DRAW_LINE,
            {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "color": color, "width": width},
            thought=thought,
            layer_id=layer_id
        )
        return self.queue_command(cmd)
        
    def draw_rectangle(
        self,
        x: float, y: float, width: float, height: float,
        stroke_color: str = "#000000",
        fill_color: Optional[str] = None,
        stroke_width: float = 2,
        thought: Optional[str] = None,
        layer_id: Optional[str] = None
    ) -> str:
        """Queue a rectangle drawing command."""
        cmd = self.create_draw_command(
            CommandType.DRAW_RECTANGLE,
            {
                "x": x, "y": y, "width": width, "height": height,
                "strokeColor": stroke_color, "fillColor": fill_color,
                "strokeWidth": stroke_width
            },
            thought=thought,
            layer_id=layer_id
        )
        return self.queue_command(cmd)
        
    def draw_ellipse(
        self,
        cx: float, cy: float, rx: float, ry: float,
        stroke_color: str = "#000000",
        fill_color: Optional[str] = None,
        stroke_width: float = 2,
        thought: Optional[str] = None,
        layer_id: Optional[str] = None
    ) -> str:
        """Queue an ellipse drawing command."""
        cmd = self.create_draw_command(
            CommandType.DRAW_ELLIPSE,
            {
                "cx": cx, "cy": cy, "rx": rx, "ry": ry,
                "strokeColor": stroke_color, "fillColor": fill_color,
                "strokeWidth": stroke_width
            },
            thought=thought,
            layer_id=layer_id
        )
        return self.queue_command(cmd)
        
    def draw_text(
        self,
        x: float, y: float, text: str,
        font_size: int = 16,
        font_family: str = "Arial",
        color: str = "#000000",
        thought: Optional[str] = None,
        layer_id: Optional[str] = None
    ) -> str:
        """Queue a text drawing command."""
        cmd = self.create_draw_command(
            CommandType.DRAW_TEXT,
            {
                "x": x, "y": y, "text": text,
                "fontSize": font_size, "fontFamily": font_family,
                "color": color
            },
            thought=thought,
            layer_id=layer_id
        )
        return self.queue_command(cmd)
        
    def draw_arrow(
        self,
        x1: float, y1: float, x2: float, y2: float,
        color: str = "#000000",
        width: float = 2,
        head_size: float = 10,
        thought: Optional[str] = None,
        layer_id: Optional[str] = None
    ) -> str:
        """Queue an arrow drawing command."""
        cmd = self.create_draw_command(
            CommandType.DRAW_ARROW,
            {
                "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                "color": color, "width": width, "headSize": head_size
            },
            thought=thought,
            layer_id=layer_id
        )
        return self.queue_command(cmd)
        
    def draw_image(
        self,
        url: str,
        x: float, y: float,
        width: float = 200,
        height: float = 200,
        caption: Optional[str] = None,
        thought: Optional[str] = None,
        layer_id: Optional[str] = None
    ) -> str:
        """Queue an image drawing command."""
        cmd = self.create_draw_command(
            CommandType.DRAW_IMAGE,
            {
                "url": url, "x": x, "y": y, 
                "width": width, "height": height,
                "caption": caption
            },
            thought=thought,
            layer_id=layer_id
        )
        return self.queue_command(cmd)
        
    # === CAD Commands ===
    
    def draw_wall(
        self,
        x1: float, y1: float, x2: float, y2: float,
        thickness: float = 6,
        color: str = "#333333",
        thought: Optional[str] = None
    ) -> str:
        """Queue a wall drawing command (CAD mode)."""
        cmd = self.create_draw_command(
            CommandType.DRAW_WALL,
            {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "thickness": thickness, "color": color},
            thought=thought,
            layer_id="cad"
        )
        return self.queue_command(cmd)
        
    def draw_door(
        self,
        x: float, y: float, width: float = 36, angle: float = 0,
        swing: str = "left",
        thought: Optional[str] = None
    ) -> str:
        """Queue a door drawing command (CAD mode)."""
        cmd = self.create_draw_command(
            CommandType.DRAW_DOOR,
            {"x": x, "y": y, "width": width, "angle": angle, "swing": swing},
            thought=thought,
            layer_id="cad"
        )
        return self.queue_command(cmd)
        
    def draw_window(
        self,
        x: float, y: float, width: float = 36,
        angle: float = 0,
        thought: Optional[str] = None
    ) -> str:
        """Queue a window drawing command (CAD mode)."""
        cmd = self.create_draw_command(
            CommandType.DRAW_WINDOW,
            {"x": x, "y": y, "width": width, "angle": angle},
            thought=thought,
            layer_id="cad"
        )
        return self.queue_command(cmd)
        
    def draw_dimension(
        self,
        x1: float, y1: float, x2: float, y2: float,
        offset: float = 20,
        unit: str = "ft",
        thought: Optional[str] = None
    ) -> str:
        """Queue a dimension annotation command (CAD mode)."""
        cmd = self.create_draw_command(
            CommandType.DRAW_DIMENSION,
            {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "offset": offset, "unit": unit},
            thought=thought,
            layer_id="cad"
        )
        return self.queue_command(cmd)
        
    # === Complex Command Generators ===
    
    def generate_floor_plan(
        self,
        rooms: List[Dict[str, Any]],
        scale: float = 10,  # pixels per foot
        thought: Optional[str] = None
    ) -> str:
        """
        Generate a complete floor plan from room specifications.
        
        Each room should have: name, width, height, x, y, doors[], windows[]
        """
        cmd = self.create_draw_command(
            CommandType.GENERATE_FLOOR_PLAN,
            {"rooms": rooms, "scale": scale},
            thought=thought or "Generating floor plan layout...",
            layer_id="cad",
            priority=10
        )
        return self.queue_command(cmd)
        
    def generate_flowchart(
        self,
        nodes: List[Dict[str, Any]],
        connections: List[Dict[str, Any]],
        layout: str = "vertical",
        thought: Optional[str] = None
    ) -> str:
        """
        Generate a flowchart from nodes and connections.
        
        Nodes: {id, label, type: start|end|process|decision, x?, y?}
        Connections: {from_id, to_id, label?}
        """
        cmd = self.create_draw_command(
            CommandType.GENERATE_FLOWCHART,
            {"nodes": nodes, "connections": connections, "layout": layout},
            thought=thought or "Creating flowchart diagram...",
            layer_id="diagram",
            priority=10
        )
        return self.queue_command(cmd)
        
    def render_poem(
        self,
        title: str,
        lines: List[str],
        style: str = "classic",
        x: float = 50,
        y: float = 50,
        thought: Optional[str] = None
    ) -> str:
        """
        Render a poem with artistic typography.
        
        Styles: classic, modern, handwritten, gothic
        """
        cmd = self.create_draw_command(
            CommandType.RENDER_POEM,
            {"title": title, "lines": lines, "style": style, "x": x, "y": y},
            thought=thought or f'Rendering poem: "{title}"',
            layer_id="text",
            priority=5
        )
        return self.queue_command(cmd)
        
    # === Canvas Control Commands ===
    
    def set_mode(self, mode: str, thought: Optional[str] = None) -> str:
        """Switch canvas mode: SKETCH, DIAGRAM, CAD, MEDIA, TEXT."""
        cmd = self.create_draw_command(
            CommandType.SET_MODE,
            {"mode": mode.upper()},
            thought=thought
        )
        return self.queue_command(cmd)
        
    def set_zoom(self, zoom: float, thought: Optional[str] = None) -> str:
        """Set canvas zoom level (0.1 to 5.0)."""
        cmd = self.create_draw_command(
            CommandType.SET_ZOOM,
            {"zoom": max(0.1, min(5.0, zoom))},
            thought=thought
        )
        return self.queue_command(cmd)
        
    def pan_to(self, x: float, y: float, thought: Optional[str] = None) -> str:
        """Pan canvas to specific coordinates."""
        cmd = self.create_draw_command(
            CommandType.PAN_TO,
            {"x": x, "y": y},
            thought=thought
        )
        return self.queue_command(cmd)
        
    def clear_canvas(self, thought: Optional[str] = None) -> str:
        """Clear entire canvas."""
        cmd = self.create_draw_command(
            CommandType.CLEAR_CANVAS,
            {},
            thought=thought or "Clearing canvas..."
        )
        return self.queue_command(cmd)
        
    def clear_layer(self, layer_id: str, thought: Optional[str] = None) -> str:
        """Clear a specific layer."""
        cmd = self.create_draw_command(
            CommandType.CLEAR_LAYER,
            {"layer_id": layer_id},
            thought=thought
        )
        return self.queue_command(cmd)
        
    # === Export Commands ===
    
    def export_canvas(
        self,
        format: str = "png",
        filename: Optional[str] = None,
        thought: Optional[str] = None
    ) -> str:
        """Export canvas to file. Formats: png, svg, pdf, dxf, json."""
        cmd = self.create_draw_command(
            CommandType.EXPORT_CANVAS,
            {"format": format.lower(), "filename": filename},
            thought=thought or f"Exporting canvas as {format.upper()}..."
        )
        return self.queue_command(cmd)
        
    # === NLP Command Parser ===
    
    def parse_natural_language(self, text: str) -> List[DrawCommand]:
        """
        Parse natural language instructions into draw commands.
        
        This is a simple pattern matcher. In production, this would
        integrate with an LLM for more sophisticated parsing.
        """
        commands = []
        text_lower = text.lower()
        
        # Floor plan detection
        if "floor plan" in text_lower or "layout" in text_lower:
            commands.append(self.create_draw_command(
                CommandType.SET_MODE,
                {"mode": "CAD"},
                thought="Switching to CAD mode for floor plan"
            ))
            
        # Flowchart detection
        elif "flowchart" in text_lower or "diagram" in text_lower:
            commands.append(self.create_draw_command(
                CommandType.SET_MODE,
                {"mode": "DIAGRAM"},
                thought="Switching to Diagram mode"
            ))
            
        # Poem detection
        elif "poem" in text_lower or "verse" in text_lower:
            commands.append(self.create_draw_command(
                CommandType.SET_MODE,
                {"mode": "TEXT"},
                thought="Switching to Text mode for poetry"
            ))
            
        # Clear detection
        elif "clear" in text_lower or "reset" in text_lower:
            commands.append(self.create_draw_command(
                CommandType.CLEAR_CANVAS,
                {},
                thought="Clearing the canvas"
            ))
            
        return commands
        
    # === MCP Tool Definitions ===
    
    def get_mcp_tools(self) -> List[Dict[str, Any]]:
        """
        Get MCP tool definitions for the Canvas.
        
        These can be registered with an MCP server to allow
        AI agents to interact with the canvas.
        """
        return [
            {
                "name": "canvas_draw_shape",
                "description": "Draw a shape on the Canvas canvas",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "shape": {
                            "type": "string",
                            "enum": ["line", "rectangle", "ellipse", "arrow"],
                            "description": "Type of shape to draw"
                        },
                        "coordinates": {
                            "type": "object",
                            "description": "Shape coordinates (x1,y1,x2,y2 for lines; x,y,width,height for rect)"
                        },
                        "style": {
                            "type": "object",
                            "properties": {
                                "strokeColor": {"type": "string"},
                                "fillColor": {"type": "string"},
                                "strokeWidth": {"type": "number"}
                            }
                        },
                        "thought": {"type": "string", "description": "Explanation of what you're drawing"}
                    },
                    "required": ["shape", "coordinates"]
                }
            },
            {
                "name": "canvas_draw_text",
                "description": "Add text to the Canvas canvas",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Text content to display"},
                        "x": {"type": "number", "description": "X position"},
                        "y": {"type": "number", "description": "Y position"},
                        "fontSize": {"type": "number", "description": "Font size in pixels"},
                        "color": {"type": "string", "description": "Text color"},
                        "thought": {"type": "string"}
                    },
                    "required": ["text", "x", "y"]
                }
            },
            {
                "name": "canvas_draw_image",
                "description": "Add an image to the Canvas canvas",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "Image URL"},
                        "x": {"type": "number", "description": "X position"},
                        "y": {"type": "number", "description": "Y position"},
                        "width": {"type": "number", "description": "Width"},
                        "height": {"type": "number", "description": "Height"},
                        "caption": {"type": "string", "description": "Optional caption"},
                        "thought": {"type": "string"}
                    },
                    "required": ["url", "x", "y"]
                }
            },
            {
                "name": "canvas_floor_plan",
                "description": "Generate a floor plan with rooms, doors, and windows",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "rooms": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "width": {"type": "number", "description": "Width in feet"},
                                    "height": {"type": "number", "description": "Height in feet"},
                                    "x": {"type": "number"},
                                    "y": {"type": "number"},
                                    "doors": {"type": "array"},
                                    "windows": {"type": "array"}
                                }
                            },
                            "description": "Array of room specifications"
                        },
                        "thought": {"type": "string"}
                    },
                    "required": ["rooms"]
                }
            },
            {
                "name": "canvas_flowchart",
                "description": "Generate a flowchart diagram",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "nodes": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "label": {"type": "string"},
                                    "type": {"type": "string", "enum": ["start", "end", "process", "decision"]}
                                }
                            }
                        },
                        "connections": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "from": {"type": "string"},
                                    "to": {"type": "string"},
                                    "label": {"type": "string"}
                                }
                            }
                        },
                        "thought": {"type": "string"}
                    },
                    "required": ["nodes", "connections"]
                }
            },
            {
                "name": "canvas_poem",
                "description": "Render a poem with artistic typography",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "lines": {"type": "array", "items": {"type": "string"}},
                        "style": {"type": "string", "enum": ["classic", "modern", "handwritten", "gothic"]},
                        "thought": {"type": "string"}
                    },
                    "required": ["title", "lines"]
                }
            },
            {
                "name": "canvas_export",
                "description": "Export the canvas to a file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "format": {"type": "string", "enum": ["png", "svg", "pdf", "dxf", "json"]},
                        "filename": {"type": "string"}
                    },
                    "required": ["format"]
                }
            },
            {
                "name": "canvas_control",
                "description": "Control the canvas (clear, zoom, pan, change mode)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["clear", "zoom", "pan", "mode"]},
                        "value": {"type": ["string", "number", "object"]},
                        "thought": {"type": "string"}
                    },
                    "required": ["action"]
                }
            }
        ]
        
    async def handle_mcp_tool_call(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle an MCP tool call and return the result.
        """
        thought = parameters.get("thought")
        
        try:
            if tool_name == "canvas_draw_shape":
                shape = parameters["shape"]
                coords = parameters["coordinates"]
                style = parameters.get("style", {})
                
                if shape == "line":
                    cmd_id = self.draw_line(
                        coords.get("x1", 0), coords.get("y1", 0),
                        coords.get("x2", 100), coords.get("y2", 100),
                        color=style.get("strokeColor", "#000000"),
                        width=style.get("strokeWidth", 2),
                        thought=thought
                    )
                elif shape == "rectangle":
                    cmd_id = self.draw_rectangle(
                        coords.get("x", 0), coords.get("y", 0),
                        coords.get("width", 100), coords.get("height", 100),
                        stroke_color=style.get("strokeColor", "#000000"),
                        fill_color=style.get("fillColor"),
                        stroke_width=style.get("strokeWidth", 2),
                        thought=thought
                    )
                elif shape == "ellipse":
                    cmd_id = self.draw_ellipse(
                        coords.get("cx", 50), coords.get("cy", 50),
                        coords.get("rx", 50), coords.get("ry", 50),
                        stroke_color=style.get("strokeColor", "#000000"),
                        fill_color=style.get("fillColor"),
                        stroke_width=style.get("strokeWidth", 2),
                        thought=thought
                    )
                elif shape == "arrow":
                    cmd_id = self.draw_arrow(
                        coords.get("x1", 0), coords.get("y1", 0),
                        coords.get("x2", 100), coords.get("y2", 100),
                        color=style.get("strokeColor", "#000000"),
                        width=style.get("strokeWidth", 2),
                        thought=thought
                    )
                else:
                    return {"success": False, "error": f"Unknown shape: {shape}"}
                    
                return {"success": True, "command_id": cmd_id}
                
            elif tool_name == "canvas_draw_text":
                cmd_id = self.draw_text(
                    parameters["x"], parameters["y"], parameters["text"],
                    font_size=parameters.get("fontSize", 16),
                    color=parameters.get("color", "#000000"),
                    thought=thought
                )
                return {"success": True, "command_id": cmd_id}
                
            elif tool_name == "canvas_draw_image":
                cmd_id = self.draw_image(
                    parameters["url"],
                    parameters["x"], parameters["y"],
                    width=parameters.get("width", 200),
                    height=parameters.get("height", 200),
                    caption=parameters.get("caption"),
                    thought=thought
                )
                return {"success": True, "command_id": cmd_id}
                
            elif tool_name == "canvas_floor_plan":
                cmd_id = self.generate_floor_plan(
                    parameters["rooms"],
                    scale=parameters.get("scale", 10),
                    thought=thought
                )
                return {"success": True, "command_id": cmd_id}
                
            elif tool_name == "canvas_flowchart":
                cmd_id = self.generate_flowchart(
                    parameters["nodes"],
                    parameters["connections"],
                    layout=parameters.get("layout", "vertical"),
                    thought=thought
                )
                return {"success": True, "command_id": cmd_id}
                
            elif tool_name == "canvas_poem":
                cmd_id = self.render_poem(
                    parameters["title"],
                    parameters["lines"],
                    style=parameters.get("style", "classic"),
                    thought=thought
                )
                return {"success": True, "command_id": cmd_id}
                
            elif tool_name == "canvas_export":
                cmd_id = self.export_canvas(
                    format=parameters["format"],
                    filename=parameters.get("filename"),
                    thought=thought
                )
                return {"success": True, "command_id": cmd_id}
                
            elif tool_name == "canvas_control":
                action = parameters["action"]
                value = parameters.get("value")
                
                if action == "clear":
                    cmd_id = self.clear_canvas(thought=thought)
                elif action == "zoom":
                    cmd_id = self.set_zoom(float(value), thought=thought)
                elif action == "pan" and isinstance(value, dict):
                    cmd_id = self.pan_to(value.get("x", 0), value.get("y", 0), thought=thought)
                elif action == "mode":
                    cmd_id = self.set_mode(str(value), thought=thought)
                else:
                    return {"success": False, "error": f"Unknown action: {action}"}
                    
                return {"success": True, "command_id": cmd_id}
                
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}
                
        except Exception as e:
            logger.error(f"Error handling MCP tool call: {e}")
            return {"success": False, "error": str(e)}


# Global controller instance
canvas_controller = CanvasMCPController()


# === Convenience functions for agent integration ===

def get_pending_draw_commands() -> List[Dict[str, Any]]:
    """Get all pending draw commands."""
    return canvas_controller.get_pending_commands()


def execute_draw_command(command_type: str, parameters: Dict[str, Any], thought: Optional[str] = None) -> str:
    """Execute a draw command by type."""
    try:
        cmd_type = CommandType(command_type)
        cmd = canvas_controller.create_draw_command(cmd_type, parameters, thought=thought)
        return canvas_controller.queue_command(cmd)
    except ValueError:
        raise ValueError(f"Unknown command type: {command_type}")


def register_mcp_tools(mcp_server):
    """Register Canvas tools with an MCP server."""
    tools = canvas_controller.get_mcp_tools()
    for tool in tools:
        try:
            # Some MCP server APIs expose `register_tool(name, spec)`
            if hasattr(mcp_server, "register_tool"):
                mcp_server.register_tool(tool["name"], tool)
            # FastMCP exposes `add_tool(tool_object)`; attempt to import AgentTool
            elif hasattr(mcp_server, "add_tool"):
                try:
                    from agent_mcp.server import AgentTool
                    # Build a simple wrapper function that calls our handler
                    def _make_fn(_name):
                        def _fn(**arguments):
                            return canvas_controller.handle_mcp_tool_call(_name, arguments)
                        return _fn

                    AT = AgentTool(
                        name=tool["name"],
                        description=tool.get("description"),
                        parameters=tool.get("parameters", {"type": "object"}),
                        output_schema=None,
                        annotations=None,
                        serializer=None,
                        tags={tool.get("category", "canvas")},
                        meta={"category": tool.get("category", "canvas"), "source": "Canvas"},
                        fn=_make_fn(tool["name"]),
                    )
                    mcp_server.add_tool(AT)
                except Exception:
                    # Can't add in this environment
                    pass
            else:
                # Unknown server API
                pass
        except Exception:
            continue
    return tools
