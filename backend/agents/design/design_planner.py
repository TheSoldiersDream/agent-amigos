"""
Design Planner - High-Level Design Orchestration
=================================================

Coordinates the Think → Draw → Explain loop.
Main entry point for design agent capabilities.
"""

import logging
from typing import Dict, Any, Optional
from .spatial_reasoning import SpatialReasoning, DesignPlan
from .drawing_executor import DrawingExecutor
from .design_memory import DesignMemory

logger = logging.getLogger(__name__)


class DesignPlanner:
    """
    High-level orchestrator for design workflow.
    
    Workflow:
    1. Understand design goal
    2. Use SpatialReasoning to create plan
    3. Use DrawingExecutor to draw on Canvas
    4. Save to DesignMemory
    5. Support iterative refinement
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.reasoner = SpatialReasoning()
        self.executor = DrawingExecutor(session_id)
        self.memory = DesignMemory()
        self.current_plan: Optional[DesignPlan] = None
    
    def design(self, goal: str, narrate: bool = True) -> Dict[str, Any]:
        """
        Main design entry point.
        
        Args:
            goal: Natural language design goal
            narrate: Whether to narrate design process
        
        Returns:
            Complete design result with narration and Canvas commands
        """
        logger.info(f"🎯 Starting design: {goal}")
        
        # Step 1: Spatial Reasoning - Create plan
        logger.info("🧠 Analyzing spatial requirements...")
        plan = self.reasoner.create_design_plan(goal)
        self.current_plan = plan
        
        # Step 2: Execute plan on Canvas
        logger.info("🎨 Drawing design on Canvas...")
        execution_result = self.executor.execute_design_plan(plan, narrate=narrate)
        
        # Step 3: Save to memory
        logger.info("💾 Saving design to memory...")
        session_id = self.memory.save_design(
            plan,
            pass_number=self.executor.design_pass,
            execution_data=execution_result
        )
        
        # Compile complete result
        result = {
            "success": True,
            "goal": goal,
            "plan": {
                "layout": plan.layout_strategy,
                "rooms": len(plan.rooms),
                "total_area": plan.total_area,
                "principles": plan.design_principles
            },
            "canvas_commands": execution_result["commands"],
            "narration": execution_result["narration"],
            "explanation": execution_result["explanation"],
            "session_id": session_id,
            "design_pass": self.executor.design_pass
        }
        
        logger.info(f"✓ Design complete: {session_id}")
        return result
    
    def refine(self, feedback: str, narrate: bool = True) -> Dict[str, Any]:
        """
        Refine current design based on feedback.
        
        Examples:
        - "Make the living room bigger"
        - "Add a balcony facing north"
        - "Improve ventilation"
        """
        if not self.current_plan:
            logger.error("No active design to refine")
            return {
                "success": False,
                "error": "No active design. Please create a design first."
            }
        
        logger.info(f"🔄 Refining design: {feedback}")
        
        # Execute refinement
        execution_result = self.executor.refine_design(feedback, narrate=narrate)
        
        # Update memory with refined version
        session_id = self.memory.save_design(
            self.current_plan,
            pass_number=self.executor.design_pass,
            execution_data=execution_result
        )
        
        result = {
            "success": True,
            "feedback": feedback,
            "canvas_commands": execution_result["commands"],
            "narration": execution_result["narration"],
            "explanation": execution_result.get("explanation", ""),
            "session_id": session_id,
            "design_pass": self.executor.design_pass
        }
        
        logger.info(f"✓ Refinement complete: {session_id}")
        return result
    
    def iterate(self, goal: str, passes: int = 3, narrate: bool = True) -> Dict[str, Any]:
        """
        Multi-pass design iteration.
        
        Pass 1: Concept sketch
        Pass 2: Refined diagram
        Pass 3: Scaled CAD plan
        """
        logger.info(f"🔁 Starting {passes}-pass iteration for: {goal}")
        
        results = []
        
        for pass_num in range(1, passes + 1):
            logger.info(f"Pass {pass_num}/{passes}")
            
            if pass_num == 1:
                # Initial design
                result = self.design(goal, narrate=narrate)
            else:
                # Refinement passes
                refinement_feedback = self._generate_auto_refinement(pass_num)
                result = self.refine(refinement_feedback, narrate=narrate)
            
            results.append(result)
        
        return {
            "success": True,
            "goal": goal,
            "passes_completed": passes,
            "results": results,
            "final_session": results[-1]["session_id"] if results else None
        }
    
    def _generate_auto_refinement(self, pass_num: int) -> str:
        """Generate automatic refinement feedback for iteration passes"""
        if pass_num == 2:
            return "Refine room proportions and add more detail"
        elif pass_num == 3:
            return "Add scaled dimensions and detailed annotations"
        else:
            return "Further detail and clarity"
    
    def load_previous_design(self, session_id: str) -> Dict[str, Any]:
        """Load a previous design from memory"""
        design_data = self.memory.load_design(session_id)
        
        if not design_data:
            return {
                "success": False,
                "error": f"Design not found: {session_id}"
            }
        
        return {
            "success": True,
            "design": design_data
        }
    
    def list_recent_designs(self, limit: int = 10) -> Dict[str, Any]:
        """List recent designs"""
        designs = self.memory.list_designs(limit=limit)
        
        return {
            "success": True,
            "count": len(designs),
            "designs": designs
        }
