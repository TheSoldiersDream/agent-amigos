"""
Drawing Executor - Think → Draw → Explain Loop
===============================================

Executes design plans by calling Canvas API.
Narrates the design process while drawing.
"""

import logging
from typing import Optional, List, Dict, Any
from .canvas_controller import CanvasController
from .spatial_reasoning import DesignPlan, Room, Connection
from .annotation_engine import AnnotationEngine

logger = logging.getLogger(__name__)


class DrawingExecutor:
    """
    Executes spatial design plans on Canvas.
    
    Workflow:
    1. Understand design goal
    2. Break into spatial components
    3. Select Canvas mode
    4. Draw first-pass layout
    5. Annotate key elements
    6. Explain what was drawn
    7. Ask for refinement or continue
    """
    
    def __init__(self, session_id: str):
        self.canvas = CanvasController(session_id)
        self.annotator = AnnotationEngine(self.canvas)
        self.current_plan: Optional[DesignPlan] = None
        self.execution_log = []
        self.design_pass = 0  # 0=concept, 1=refined, 2=scaled, 3=detailed
    
    def execute_design_plan(self, plan: DesignPlan, narrate: bool = True) -> Dict[str, Any]:
        """
        Main execution entry point.
        Takes a DesignPlan and draws it on Canvas.
        
        Returns: Execution result with narration and commands
        """
        self.current_plan = plan
        self.design_pass += 1
        self.execution_log = []
        
        # Step 1: Set Canvas mode based on design pass
        if self.design_pass == 1:
            self.canvas.set_mode("SKETCH")
            self._log("Starting conceptual sketch pass", narrate)
        elif self.design_pass == 2:
            self.canvas.set_mode("DIAGRAM")
            self._log("Refining layout with diagram view", narrate)
        elif self.design_pass >= 3:
            self.canvas.set_mode("CAD")
            self.canvas.set_scale(plan.scale, "meters")
            self._log(f"Creating scaled architectural plan at {plan.scale}px/m", narrate)
        
        # Step 2: Draw base layout
        self._log(f"Planning {plan.layout_strategy} layout for {len(plan.rooms)} rooms", narrate)
        result = self._draw_layout(plan, narrate)
        
        # Step 3: Add connections (doors, openings)
        self._log(f"Adding {len(plan.connections)} connections between spaces", narrate)
        self._draw_connections(plan, narrate)
        
        # Step 4: Annotate
        self._log("Annotating dimensions and labels", narrate)
        self.annotator.annotate_design(plan)
        
        # Step 5: Explain design principles
        explanation = self._generate_explanation(plan, narrate)
        
        return {
            "success": True,
            "plan": plan,
            "commands": self.canvas.get_commands(),
            "narration": self.execution_log,
            "explanation": explanation,
            "design_pass": self.design_pass
        }
    
    def _draw_layout(self, plan: DesignPlan, narrate: bool) -> Dict[str, Any]:
        """Draw all rooms according to layout strategy"""
        
        for room in plan.rooms:
            self._draw_room_with_narration(room, plan, narrate)
        
        return {"rooms_drawn": len(plan.rooms)}
    
    def _draw_room_with_narration(self, room: Room, plan: DesignPlan, narrate: bool):
        """Draw a single room with human-like narration"""
        
        # Narrate placement reasoning
        reasoning = self._generate_room_reasoning(room, plan)
        self._log(reasoning, narrate)
        
        # Calculate scaled dimensions
        x = room.x
        y = room.y
        width_px = room.width * plan.scale
        height_px = room.height * plan.scale
        
        # Draw room on appropriate layer
        self.canvas.draw_room(x, y, width_px, height_px, room.name, color="#333333")
        
        # Add windows if natural light is important
        if room.natural_light and self.design_pass >= 2:
            self._add_windows(room, x, y, width_px, height_px, narrate)
    
    def _generate_room_reasoning(self, room: Room, plan: DesignPlan) -> str:
        """Generate human-like reasoning for room placement"""
        
        reasons = []
        
        # Orientation reasoning
        if room.preferred_orientation:
            reasons.append(f"orienting {room.name} to the {room.preferred_orientation.value} for optimal lighting")
        
        # Adjacency reasoning
        if room.adjacency_preferences:
            prefs = ", ".join(room.adjacency_preferences)
            reasons.append(f"placing near {prefs} for convenient flow")
        
        # Climate reasoning
        if plan.design_principles:
            if "cross ventilation" in " ".join(plan.design_principles).lower():
                if room.ventilation:
                    reasons.append("positioned for cross-ventilation")
        
        # Area reasoning
        area = room.area()
        reasons.append(f"sized at {area:.1f}m² for {room.type.value}")
        
        if reasons:
            return f"Placing {room.name}: {', '.join(reasons)}"
        else:
            return f"Drawing {room.name} at {room.x}, {room.y}"
    
    def _add_windows(self, room: Room, x: float, y: float, width: float, height: float, narrate: bool):
        """Add windows to room for natural light"""
        window_width = 40
        window_height = 10
        
        # Add window on one wall (simplified for concept)
        window_x = x + width - window_width - 10
        window_y = y + height / 2 - window_height / 2
        
        self.canvas.draw_window(window_x, window_y, window_width, window_height)
        self._log(f"Adding window to {room.name} for natural light", narrate)
    
    def _draw_connections(self, plan: DesignPlan, narrate: bool):
        """Draw doors and openings between rooms"""
        
        for conn in plan.connections:
            room1 = plan.get_room(conn.room1)
            room2 = plan.get_room(conn.room2)
            
            if not room1 or not room2:
                continue
            
            # Calculate door position (simplified - at room boundary)
            if room1.x and room1.y and room2.x and room2.y:
                # Determine wall between rooms
                door_x, door_y = self._calculate_door_position(room1, room2, plan.scale)
                
                door_width_px = conn.width * plan.scale
                
                self.canvas.draw_door(door_x, door_y, door_width_px, orientation="right")
                
                connection_desc = f"{conn.type} between {conn.room1} and {conn.room2}"
                self._log(f"Adding {connection_desc}", narrate)
    
    def _calculate_door_position(self, room1: Room, room2: Room, scale: float) -> tuple:
        """Calculate optimal door position between two rooms"""
        # Simplified: place at midpoint of shared wall
        r1_center_x = room1.x + (room1.width * scale / 2)
        r1_center_y = room1.y + (room1.height * scale / 2)
        
        r2_center_x = room2.x + (room2.width * scale / 2)
        r2_center_y = room2.y + (room2.height * scale / 2)
        
        # Average position
        door_x = (r1_center_x + r2_center_x) / 2
        door_y = (r1_center_y + r2_center_y) / 2
        
        return (door_x, door_y)
    
    def _generate_explanation(self, plan: DesignPlan, narrate: bool) -> str:
        """Generate human-readable explanation of the design"""
        
        explanation_parts = [
            f"**Design Summary:**",
            f"I've created a {plan.layout_strategy} layout with {len(plan.rooms)} rooms totaling {plan.total_area:.1f}m².",
            "",
            "**Key Design Principles:**"
        ]
        
        for principle in plan.design_principles:
            explanation_parts.append(f"- {principle}")
        
        explanation_parts.append("")
        explanation_parts.append("**Room Layout:**")
        
        for room in plan.rooms:
            explanation_parts.append(f"- **{room.name}** ({room.area():.1f}m²): {room.type.value}")
        
        explanation = "\n".join(explanation_parts)
        # Log explanation as separate lines to avoid character iteration bug
        for line in explanation_parts:
            self._log(line, narrate)
        
        return explanation
    
    def _log(self, message: str, narrate: bool = True):
        """Log execution step with optional narration"""
        self.execution_log.append(message)
        if narrate:
            logger.info(f"🎨 {message}")
    
    def refine_design(self, feedback: str, narrate: bool = True) -> Dict[str, Any]:
        """
        Refine current design based on feedback.
        
        Examples:
        - "Make the kitchen bigger"
        - "Add a balcony"
        - "Change bedroom orientation"
        """
        if not self.current_plan:
            return {"success": False, "error": "No active design to refine"}
        
        self._log(f"Refining design based on: {feedback}", narrate)
        
        # Parse feedback and modify plan
        modified_plan = self._apply_feedback(self.current_plan, feedback)
        
        # Re-execute with modifications
        return self.execute_design_plan(modified_plan, narrate)
    
    def _apply_feedback(self, plan: DesignPlan, feedback: str) -> DesignPlan:
        """Apply user feedback to modify design plan"""
        feedback_lower = feedback.lower()
        
        # Example: "make kitchen bigger"
        if "bigger" in feedback_lower or "larger" in feedback_lower:
            for word in ["kitchen", "bedroom", "living", "bathroom"]:
                if word in feedback_lower:
                    for room in plan.rooms:
                        if word in room.name.lower():
                            room.width *= 1.2
                            room.height *= 1.2
                            logger.info(f"Increased {room.name} size by 20%")
        
        # Example: "add balcony"
        if "add" in feedback_lower:
            # TODO: Add new room to plan
            pass
        
        # Re-assign positions after modifications
        from .spatial_reasoning import SpatialReasoning
        reasoner = SpatialReasoning()
        reasoner._assign_positions(plan.rooms, plan.layout_strategy, {})
        
        return plan
    
    def get_canvas_commands(self) -> List[Dict[str, Any]]:
        """Get all Canvas drawing commands for backend"""
        return self.canvas.get_commands()
    
    def export_design_data(self) -> Dict[str, Any]:
        """Export complete design data"""
        return {
            "canvas_state": self.canvas.export_design(),
            "execution_log": self.execution_log,
            "design_pass": self.design_pass,
            "current_plan": self.current_plan.__dict__ if self.current_plan else None
        }
