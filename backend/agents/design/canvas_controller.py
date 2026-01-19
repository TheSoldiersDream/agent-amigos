"""
Canvas Controller - Direct Canvas API Interface
===============================================

Provides explicit Canvas tool control methods.
Agent calls these to draw, never hallucinates drawings.
"""

import logging
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CanvasState:
    """Current Canvas state"""
    active_layer: str = "Base"
    mode: str = "SKETCH"  # SKETCH, DIAGRAM, CAD, TEXT
    scale: float = 1.0
    canvas_width: int = 1000
    canvas_height: int = 800
    

class CanvasController:
    """
    Direct interface to Agent Amigos Canvas.
    All drawing operations go through this controller.
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.state = CanvasState()
        self.draw_commands = []  # Buffer for batch operations
        self.layers = {
            "Base": [],
            "Walls": [],
            "Doors": [],
            "Furniture": [],
            "Electrical": [],
            "Plumbing": [],
            "Annotations": []
        }
        
    # ==================== CORE DRAWING PRIMITIVES ====================
    
    def draw_line(self, x1: float, y1: float, x2: float, y2: float, 
                  color: str = "#000000", width: float = 2.0) -> Dict[str, Any]:
        """
        Draw a line on active layer.
        Returns command object for Canvas backend.
        """
        command = {
            "type": "line",
            "layer": self.state.active_layer,
            "points": [x1, y1, x2, y2],
            "color": color,
            "width": width,
            "tool": "pen"
        }
        
        self.draw_commands.append(command)
        self.layers[self.state.active_layer].append(command)
        
        logger.info(f"✏️ Drawing line from ({x1}, {y1}) to ({x2}, {y2}) on {self.state.active_layer}")
        return command
    
    def draw_rect(self, x: float, y: float, width: float, height: float,
                  color: str = "#000000", fill: Optional[str] = None, 
                  line_width: float = 2.0) -> Dict[str, Any]:
        """
        Draw rectangle (room, boundary, etc).
        """
        command = {
            "type": "rectangle",
            "layer": self.state.active_layer,
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "stroke": color,
            "fill": fill,
            "strokeWidth": line_width,
            "tool": "shapes"
        }
        
        self.draw_commands.append(command)
        self.layers[self.state.active_layer].append(command)
        
        logger.info(f"▭ Drawing rect at ({x}, {y}) size {width}x{height} on {self.state.active_layer}")
        return command
    
    def add_text(self, x: float, y: float, label: str, 
                 size: float = 16, color: str = "#000000") -> Dict[str, Any]:
        """
        Add text annotation.
        """
        command = {
            "type": "text",
            "layer": self.state.active_layer,
            "x": x,
            "y": y,
            "text": label,
            "fontSize": size,
            "color": color,
            "tool": "text"
        }
        
        self.draw_commands.append(command)
        self.layers[self.state.active_layer].append(command)
        
        logger.info(f"📝 Adding text '{label}' at ({x}, {y}) on {self.state.active_layer}")
        return command
    
    def draw_circle(self, cx: float, cy: float, radius: float,
                   color: str = "#000000", fill: Optional[str] = None) -> Dict[str, Any]:
        """Draw circle (for fixtures, furniture markers, etc)."""
        command = {
            "type": "circle",
            "layer": self.state.active_layer,
            "cx": cx,
            "cy": cy,
            "radius": radius,
            "stroke": color,
            "fill": fill,
            "tool": "shapes"
        }
        
        self.draw_commands.append(command)
        self.layers[self.state.active_layer].append(command)
        
        logger.info(f"⭕ Drawing circle at ({cx}, {cy}) r={radius} on {self.state.active_layer}")
        return command
    
    def draw_arc(self, cx: float, cy: float, radius: float, 
                 start_angle: float, end_angle: float,
                 color: str = "#000000") -> Dict[str, Any]:
        """Draw arc (for door swings, etc)."""
        command = {
            "type": "arc",
            "layer": self.state.active_layer,
            "cx": cx,
            "cy": cy,
            "radius": radius,
            "startAngle": start_angle,
            "endAngle": end_angle,
            "stroke": color,
            "tool": "shapes"
        }
        
        self.draw_commands.append(command)
        self.layers[self.state.active_layer].append(command)
        
        logger.info(f"⌒ Drawing arc at ({cx}, {cy}) on {self.state.active_layer}")
        return command
    
    # ==================== LAYER MANAGEMENT ====================
    
    def set_layer(self, layer_name: str):
        """Switch active drawing layer."""
        if layer_name not in self.layers:
            self.layers[layer_name] = []
            logger.warning(f"Creating new layer: {layer_name}")
        
        self.state.active_layer = layer_name
        logger.info(f"🎨 Switched to layer: {layer_name}")
    
    def clear_layer(self, layer_name: str):
        """Clear all content from a layer."""
        if layer_name in self.layers:
            self.layers[layer_name] = []
            logger.info(f"🧹 Cleared layer: {layer_name}")
    
    def hide_layer(self, layer_name: str):
        """Hide layer (keep content but don't render)."""
        command = {"type": "hide_layer", "layer": layer_name}
        self.draw_commands.append(command)
        logger.info(f"👁️‍🗨️ Hiding layer: {layer_name}")
    
    def show_layer(self, layer_name: str):
        """Show previously hidden layer."""
        command = {"type": "show_layer", "layer": layer_name}
        self.draw_commands.append(command)
        logger.info(f"👁️ Showing layer: {layer_name}")
    
    # ==================== MODE & SCALE CONTROL ====================
    
    def set_mode(self, mode: str):
        """
        Set Canvas mode:
        - SKETCH: Conceptual layouts
        - DIAGRAM: Room relationships & flow
        - CAD: Scaled architectural plans
        - TEXT: Annotations & measurements
        """
        valid_modes = ["SKETCH", "DIAGRAM", "CAD", "TEXT"]
        if mode.upper() not in valid_modes:
            logger.error(f"Invalid mode: {mode}. Use: {valid_modes}")
            return
        
        self.state.mode = mode.upper()
        command = {"type": "set_mode", "mode": self.state.mode}
        self.draw_commands.append(command)
        logger.info(f"🔧 Canvas mode: {self.state.mode}")
    
    def set_scale(self, scale: float, unit: str = "meters"):
        """
        Set drawing scale for CAD mode.
        Example: 1 pixel = 0.1 meters
        """
        self.state.scale = scale
        command = {"type": "set_scale", "scale": scale, "unit": unit}
        self.draw_commands.append(command)
        logger.info(f"📏 Scale set to: {scale} {unit}/px")
    
    # ==================== HIGH-LEVEL HELPERS ====================
    
    def draw_room(self, x: float, y: float, width: float, height: float, 
                  name: str, color: str = "#333333"):
        """Draw a complete room with walls and label."""
        self.set_layer("Walls")
        self.draw_rect(x, y, width, height, color=color, line_width=3.0)
        
        self.set_layer("Annotations")
        label_x = x + width / 2
        label_y = y + height / 2
        self.add_text(label_x, label_y, name, size=14)
        
        logger.info(f"🏠 Drew room '{name}' at ({x}, {y}) size {width}x{height}")
    
    def draw_door(self, x: float, y: float, width: float, 
                  orientation: str = "right", wall_thickness: float = 10):
        """
        Draw door with swing arc.
        orientation: 'right', 'left', 'up', 'down'
        """
        self.set_layer("Doors")
        
        # Door frame
        if orientation in ["right", "left"]:
            self.draw_rect(x, y, width, wall_thickness, color="#8B4513")
            # Arc for swing
            arc_x = x if orientation == "right" else x + width
            self.draw_arc(arc_x, y, width, 0, 90, color="#8B4513")
        else:
            self.draw_rect(x, y, wall_thickness, width, color="#8B4513")
            arc_y = y if orientation == "down" else y + width
            self.draw_arc(x, arc_y, width, 0, 90, color="#8B4513")
        
        logger.info(f"🚪 Drew door at ({x}, {y}) orientation: {orientation}")
    
    def draw_window(self, x: float, y: float, width: float, height: float):
        """Draw window symbol."""
        self.set_layer("Doors")  # Windows go on same layer as doors
        self.draw_rect(x, y, width, height, color="#4A90E2", line_width=2.0)
        # Cross pattern
        self.draw_line(x, y, x + width, y + height, color="#4A90E2", width=1.0)
        self.draw_line(x + width, y, x, y + height, color="#4A90E2", width=1.0)
        
        logger.info(f"🪟 Drew window at ({x}, {y})")
    
    # ==================== COMMAND BUFFER ====================
    
    def get_commands(self) -> List[Dict[str, Any]]:
        """Get all buffered drawing commands."""
        return self.draw_commands
    
    def clear_commands(self):
        """Clear command buffer after sending to Canvas backend."""
        self.draw_commands = []
    
    def get_layer_content(self, layer_name: str) -> List[Dict[str, Any]]:
        """Get all content on a specific layer."""
        return self.layers.get(layer_name, [])
    
    def export_design(self) -> Dict[str, Any]:
        """Export complete design as structured data."""
        return {
            "session_id": self.session_id,
            "mode": self.state.mode,
            "scale": self.state.scale,
            "layers": self.layers,
            "commands": self.draw_commands
        }
