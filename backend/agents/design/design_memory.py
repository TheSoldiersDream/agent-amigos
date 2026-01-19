"""
Design Memory System
====================

Stores and retrieves design plans across refinement passes.
Enables iterative design improvements without losing progress.
"""

import logging
import json
import os
from typing import Optional, List, Dict, Any
from datetime import datetime
from .spatial_reasoning import DesignPlan, Room, Connection, RoomType, Orientation

logger = logging.getLogger(__name__)


class DesignMemory:
    """
    Persistent storage for design plans and iterations.
    
    Enables:
    - Multi-pass refinement
    - Design history tracking
    - Learning from successful designs
    """
    
    def __init__(self, memory_dir: str = "data/design_memory"):
        self.memory_dir = memory_dir
        os.makedirs(memory_dir, exist_ok=True)
        self.current_session = None
    
    def save_design(self, plan: DesignPlan, pass_number: int, 
                   execution_data: Dict[str, Any]) -> str:
        """
        Save design plan and execution data.
        Returns: session_id for retrieval
        """
        timestamp = datetime.now().isoformat()
        session_id = f"design_{timestamp.replace(':', '-').replace('.', '_')}"
        
        design_data = {
            "session_id": session_id,
            "timestamp": timestamp,
            "pass_number": pass_number,
            "goal": plan.goal,
            "layout_strategy": plan.layout_strategy,
            "total_area": plan.total_area,
            "rooms": [self._serialize_room(r) for r in plan.rooms],
            "connections": [self._serialize_connection(c) for c in plan.connections],
            "design_principles": plan.design_principles,
            "execution_log": execution_data.get("narration", []),
            "canvas_commands": execution_data.get("commands", [])
        }
        
        # Save to file
        filepath = os.path.join(self.memory_dir, f"{session_id}.json")
        with open(filepath, 'w') as f:
            json.dump(design_data, f, indent=2)
        
        logger.info(f"💾 Saved design: {session_id}")
        self.current_session = session_id
        return session_id
    
    def load_design(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load design data by session ID"""
        filepath = os.path.join(self.memory_dir, f"{session_id}.json")
        
        if not os.path.exists(filepath):
            logger.error(f"Design not found: {session_id}")
            return None
        
        with open(filepath, 'r') as f:
            design_data = json.load(f)
        
        logger.info(f"📂 Loaded design: {session_id}")
        return design_data
    
    def get_latest_design(self) -> Optional[Dict[str, Any]]:
        """Get most recent design"""
        if self.current_session:
            return self.load_design(self.current_session)
        
        # Find latest file
        files = [f for f in os.listdir(self.memory_dir) if f.endswith('.json')]
        if not files:
            return None
        
        latest = max(files, key=lambda f: os.path.getmtime(os.path.join(self.memory_dir, f)))
        session_id = latest.replace('.json', '')
        return self.load_design(session_id)
    
    def list_designs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List recent designs with metadata"""
        files = [f for f in os.listdir(self.memory_dir) if f.endswith('.json')]
        files.sort(key=lambda f: os.path.getmtime(os.path.join(self.memory_dir, f)), reverse=True)
        
        designs = []
        for filename in files[:limit]:
            filepath = os.path.join(self.memory_dir, filename)
            with open(filepath, 'r') as f:
                data = json.load(f)
                designs.append({
                    "session_id": data["session_id"],
                    "timestamp": data["timestamp"],
                    "goal": data["goal"],
                    "room_count": len(data["rooms"]),
                    "total_area": data["total_area"],
                    "pass_number": data.get("pass_number", 1)
                })
        
        return designs
    
    def _serialize_room(self, room: Room) -> Dict[str, Any]:
        """Convert Room object to JSON-serializable dict"""
        return {
            "name": room.name,
            "type": room.type.value,
            "width": room.width,
            "height": room.height,
            "x": room.x,
            "y": room.y,
            "preferred_orientation": room.preferred_orientation.value if room.preferred_orientation else None,
            "natural_light": room.natural_light,
            "ventilation": room.ventilation,
            "adjacency_preferences": room.adjacency_preferences,
            "adjacency_constraints": room.adjacency_constraints
        }
    
    def _serialize_connection(self, conn: Connection) -> Dict[str, Any]:
        """Convert Connection to JSON-serializable dict"""
        return {
            "room1": conn.room1,
            "room2": conn.room2,
            "type": conn.type,
            "width": conn.width
        }
    
    def find_similar_designs(self, goal: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Find designs with similar goals (for learning)"""
        # Simple keyword matching for now
        goal_lower = goal.lower()
        keywords = set(goal_lower.split())
        
        all_designs = self.list_designs(limit=50)
        scored = []
        
        for design in all_designs:
            design_keywords = set(design["goal"].lower().split())
            similarity = len(keywords & design_keywords) / len(keywords | design_keywords)
            scored.append((similarity, design))
        
        scored.sort(reverse=True, key=lambda x: x[0])
        return [design for score, design in scored[:limit] if score > 0.2]
