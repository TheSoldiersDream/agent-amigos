"""
Annotation Engine
=================

Adds intelligent text annotations, measurements, and labels to designs.
"""

import logging
from typing import Optional, List
from .canvas_controller import CanvasController
from .spatial_reasoning import DesignPlan, Room

logger = logging.getLogger(__name__)


class AnnotationEngine:
    """
    Adds intelligent annotations to Canvas drawings.
    - Room labels
    - Dimensions
    - Measurements
    - Design notes
    """
    
    def __init__(self, canvas: CanvasController):
        self.canvas = canvas
    
    def annotate_design(self, plan: DesignPlan):
        """Add all annotations for a complete design"""
        
        # Switch to annotations layer
        self.canvas.set_layer("Annotations")
        
        # Add room labels (already done in draw_room, but can enhance)
        for room in plan.rooms:
            self._annotate_room(room, plan)
        
        # Add overall design notes
        self._add_design_notes(plan)
    
    def _annotate_room(self, room: Room, plan: DesignPlan):
        """Add detailed annotations for a room"""
        
        if not room.x or not room.y:
            return
        
        # Room dimensions
        width_m = room.width
        height_m = room.height
        area_m2 = room.area()
        
        # Position for dimension text
        x = room.x
        y = room.y
        width_px = room.width * plan.scale
        height_px = room.height * plan.scale
        
        # Add dimensions on edges
        # Width dimension (top)
        dim_text_x = x + width_px / 2
        dim_text_y = y - 15
        self.canvas.add_text(dim_text_x, dim_text_y, f"{width_m:.1f}m", size=10, color="#666")
        
        # Height dimension (right side)
        dim_text_x = x + width_px + 10
        dim_text_y = y + height_px / 2
        self.canvas.add_text(dim_text_x, dim_text_y, f"{height_m:.1f}m", size=10, color="#666")
        
        # Area annotation (inside room, bottom)
        area_text_x = x + width_px / 2
        area_text_y = y + height_px - 10
        self.canvas.add_text(area_text_x, area_text_y, f"{area_m2:.1f}m²", size=11, color="#888")
    
    def _add_design_notes(self, plan: DesignPlan):
        """Add overall design notes to canvas"""
        
        # Add title
        self.canvas.add_text(50, 30, f"Design: {plan.goal}", size=16, color="#fff")
        
        # Add layout info
        info_text = f"{plan.layout_strategy} layout • {len(plan.rooms)} rooms • {plan.total_area:.1f}m²"
        self.canvas.add_text(50, 50, info_text, size=12, color="#999")
    
    def add_measurement_line(self, x1: float, y1: float, x2: float, y2: float, 
                            label: str, color: str = "#ff9800"):
        """Add dimension line with measurement label"""
        self.canvas.set_layer("Annotations")
        
        # Draw line
        self.canvas.draw_line(x1, y1, x2, y2, color=color, width=1.0)
        
        # Add label at midpoint
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        self.canvas.add_text(mid_x, mid_y - 10, label, size=10, color=color)
    
    def add_design_note(self, x: float, y: float, note: str, color: str = "#4CAF50"):
        """Add design note/callout at specific location"""
        self.canvas.set_layer("Annotations")
        
        # Add marker
        self.canvas.draw_circle(x, y, 5, color=color, fill=color)
        
        # Add note text
        self.canvas.add_text(x + 15, y, note, size=11, color=color)
