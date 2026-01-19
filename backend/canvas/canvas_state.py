"""
🧠🎨 Agent Amigos Chalk Board - State Management

Session state management with history, persistence, and agent integration.

Created by Darrell Buttigieg (@darrellbuttigieg) #thesoldiersdream
"""

import json
import os
from datetime import datetime
from typing import Dict, Optional, List, Any
from pathlib import Path
import asyncio
from .canvas_models import (
    CanvasState, CanvasObject, Layer, HistoryEntry, SessionHistory,
    AgentDrawCommand, AgentCommandResponse, DrawMode
)


class CanvasStateManager:
    """
    Manages chalk board sessions, history, and persistence.
    """
    
    def __init__(self, storage_path: str = "./canvas_sessions"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # In-memory session storage
        self.sessions: Dict[str, CanvasState] = {}
        self.histories: Dict[str, SessionHistory] = {}
        
        # Agent command queue
        self.pending_commands: Dict[str, List[AgentDrawCommand]] = {}
        
        # Load existing sessions
        self._load_sessions()
    
    def _load_sessions(self):
        """Load sessions from disk on startup"""
        for session_file in self.storage_path.glob("*.json"):
            try:
                # Skip empty files which can occur due to interrupted writes
                if session_file.stat().st_size == 0:
                    print(f"Skipping empty session file {session_file}")
                    continue

                with open(session_file, "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                    except json.JSONDecodeError as e:
                        print(f"Skipping invalid JSON session file {session_file}: {e}")
                        continue

                    state = CanvasState(**data)
                    self.sessions[state.session_id] = state
            except Exception as e:
                print(f"Error loading session {session_file}: {e}")
    
    def _save_session(self, session_id: str):
        """Persist a session to disk"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            file_path = self.storage_path / f"{session_id}.json"
            try:
                with open(file_path, "w") as f:
                    json.dump(session.model_dump(mode="json"), f, default=str, indent=2)
            except Exception as e:
                print(f"Error saving session {session_id}: {e}")
    
    # ═══════════════════════════════════════════════════════════════
    # SESSION MANAGEMENT
    # ═══════════════════════════════════════════════════════════════
    
    def create_session(self, user_id: Optional[str] = None, title: str = "Untitled") -> CanvasState:
        """Create a new chalk board session"""
        # Default layers
        default_layers = [
            Layer(id="background", name="🖼️ Background", color="#64748b", order=0),
            Layer(id="sketch", name="✏️ Sketch", color="#ec4899", order=1),
            Layer(id="diagram", name="📊 Diagram", color="#8b5cf6", order=2),
            Layer(id="cad", name="📐 CAD", color="#06b6d4", order=3),
            Layer(id="text", name="📝 Text", color="#22c55e", order=4),
            Layer(id="media", name="🎬 Media", color="#f59e0b", order=5),
            Layer(id="annotations", name="💬 Annotations", color="#f97316", order=6),
        ]
        
        state = CanvasState(
            user_id=user_id,
            title=title,
            layers=default_layers,
        )
        
        self.sessions[state.session_id] = state
        self.histories[state.session_id] = SessionHistory(session_id=state.session_id)
        self.pending_commands[state.session_id] = []
        
        self._save_session(state.session_id)
        
        return state
    
    def get_session(self, session_id: str) -> Optional[CanvasState]:
        """Get a session by ID"""
        return self.sessions.get(session_id)

    def get_or_create_default(self) -> CanvasState:
        """Get default session or create one if it does not exist"""
        if "default" not in self.sessions:
            self.sessions["default"] = CanvasState(
                session_id="default",
                title="Agent Amigos Default Canvas",
                mode="sketch",
                layers=[]  # Empty layers, will use defaults from model
            )
            self._save_session("default")
        return self.sessions["default"]

    
    def list_sessions(self, user_id: Optional[str] = None) -> List[CanvasState]:
        """List all sessions, optionally filtered by user"""
        sessions = list(self.sessions.values())
        if user_id:
            sessions = [s for s in sessions if s.user_id == user_id]
        return sorted(sessions, key=lambda s: s.updated_at, reverse=True)
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            if session_id in self.histories:
                del self.histories[session_id]
            if session_id in self.pending_commands:
                del self.pending_commands[session_id]
            
            # Remove from disk
            file_path = self.storage_path / f"{session_id}.json"
            if file_path.exists():
                file_path.unlink()
            
            return True
        return False
    
    # ═══════════════════════════════════════════════════════════════
    # OBJECT OPERATIONS
    # ═══════════════════════════════════════════════════════════════
    
    def add_object(self, session_id: str, obj: CanvasObject) -> Optional[CanvasObject]:
        """Add an object to a session"""
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        # Record history
        self._record_history(session_id, "add", [obj.id], None, obj.model_dump())
        
        session.objects.append(obj)
        session.updated_at = datetime.utcnow()
        self._save_session(session_id)
        
        return obj
    
    def update_object(self, session_id: str, object_id: str, updates: Dict[str, Any]) -> Optional[CanvasObject]:
        """Update an object in a session"""
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        for i, obj in enumerate(session.objects):
            if obj.id == object_id:
                # Record history
                self._record_history(session_id, "update", [object_id], obj.model_dump(), updates)
                
                # Apply updates
                for key, value in updates.items():
                    if hasattr(obj, key):
                        setattr(obj, key, value)
                
                session.updated_at = datetime.utcnow()
                self._save_session(session_id)
                return obj
        
        return None
    
    def delete_object(self, session_id: str, object_id: str) -> bool:
        """Delete an object from a session"""
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        for i, obj in enumerate(session.objects):
            if obj.id == object_id:
                # Record history
                self._record_history(session_id, "delete", [object_id], obj.model_dump(), None)
                
                session.objects.pop(i)
                session.updated_at = datetime.utcnow()
                self._save_session(session_id)
                return True
        
        return False
    
    def clear_objects(self, session_id: str) -> bool:
        """Clear all objects from a session"""
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        # Record history
        self._record_history(
            session_id, "clear", 
            [obj.id for obj in session.objects],
            {"objects": [obj.model_dump() for obj in session.objects]},
            None
        )
        
        session.objects = []
        session.updated_at = datetime.utcnow()
        self._save_session(session_id)
        return True
    
    def get_objects(self, session_id: str, layer_id: Optional[str] = None) -> List[CanvasObject]:
        """Get objects from a session, optionally filtered by layer"""
        session = self.sessions.get(session_id)
        if not session:
            return []
        
        objects = session.objects
        if layer_id:
            objects = [obj for obj in objects if obj.layer_id == layer_id]
        
        return objects
    
    # ═══════════════════════════════════════════════════════════════
    # LAYER OPERATIONS
    # ═══════════════════════════════════════════════════════════════
    
    def add_layer(self, session_id: str, layer: Layer) -> Optional[Layer]:
        """Add a layer to a session"""
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        layer.order = len(session.layers)
        session.layers.append(layer)
        session.updated_at = datetime.utcnow()
        self._save_session(session_id)
        
        return layer
    
    def update_layer(self, session_id: str, layer_id: str, updates: Dict[str, Any]) -> Optional[Layer]:
        """Update a layer"""
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        for layer in session.layers:
            if layer.id == layer_id:
                for key, value in updates.items():
                    if hasattr(layer, key):
                        setattr(layer, key, value)
                session.updated_at = datetime.utcnow()
                self._save_session(session_id)
                return layer
        
        return None
    
    def delete_layer(self, session_id: str, layer_id: str) -> bool:
        """Delete a layer and its objects"""
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        # Remove layer
        session.layers = [l for l in session.layers if l.id != layer_id]
        
        # Remove objects on this layer
        session.objects = [obj for obj in session.objects if obj.layer_id != layer_id]
        
        session.updated_at = datetime.utcnow()
        self._save_session(session_id)
        return True
    
    def reorder_layers(self, session_id: str, layer_order: List[str]) -> bool:
        """Reorder layers"""
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        layer_map = {l.id: l for l in session.layers}
        reordered = []
        for i, layer_id in enumerate(layer_order):
            if layer_id in layer_map:
                layer_map[layer_id].order = i
                reordered.append(layer_map[layer_id])
        
        session.layers = reordered
        session.updated_at = datetime.utcnow()
        self._save_session(session_id)
        return True
    
    # ═══════════════════════════════════════════════════════════════
    # HISTORY / UNDO-REDO
    # ═══════════════════════════════════════════════════════════════
    
    def _record_history(self, session_id: str, action: str, object_ids: List[str],
                        previous_state: Optional[Dict], new_state: Optional[Dict]):
        """Record a history entry"""
        history = self.histories.get(session_id)
        if not history:
            return
        
        # Truncate future entries if we're not at the end
        if history.current_index < len(history.entries) - 1:
            history.entries = history.entries[:history.current_index + 1]
        
        entry = HistoryEntry(
            action=action,
            object_ids=object_ids,
            previous_state=previous_state,
            new_state=new_state,
        )
        
        history.entries.append(entry)
        history.current_index = len(history.entries) - 1
        
        # Limit history size
        if len(history.entries) > history.max_entries:
            history.entries = history.entries[-history.max_entries:]
            history.current_index = len(history.entries) - 1
    
    def undo(self, session_id: str) -> bool:
        """Undo the last action"""
        history = self.histories.get(session_id)
        session = self.sessions.get(session_id)
        if not history or not session or history.current_index < 0:
            return False
        
        entry = history.entries[history.current_index]
        
        # Reverse the action
        if entry.action == "add" and entry.new_state:
            # Remove the added object
            session.objects = [obj for obj in session.objects if obj.id not in entry.object_ids]
        elif entry.action == "delete" and entry.previous_state:
            # Restore the deleted object
            obj = CanvasObject(**entry.previous_state)
            session.objects.append(obj)
        elif entry.action == "update" and entry.previous_state:
            # Restore previous state
            for obj in session.objects:
                if obj.id in entry.object_ids:
                    for key, value in entry.previous_state.items():
                        if hasattr(obj, key):
                            setattr(obj, key, value)
        elif entry.action == "clear" and entry.previous_state:
            # Restore all cleared objects
            for obj_data in entry.previous_state.get("objects", []):
                session.objects.append(CanvasObject(**obj_data))
        
        history.current_index -= 1
        session.updated_at = datetime.utcnow()
        self._save_session(session_id)
        return True
    
    def redo(self, session_id: str) -> bool:
        """Redo the last undone action"""
        history = self.histories.get(session_id)
        session = self.sessions.get(session_id)
        if not history or not session or history.current_index >= len(history.entries) - 1:
            return False
        
        history.current_index += 1
        entry = history.entries[history.current_index]
        
        # Reapply the action
        if entry.action == "add" and entry.new_state:
            obj = CanvasObject(**entry.new_state)
            session.objects.append(obj)
        elif entry.action == "delete":
            session.objects = [obj for obj in session.objects if obj.id not in entry.object_ids]
        elif entry.action == "update" and entry.new_state:
            for obj in session.objects:
                if obj.id in entry.object_ids:
                    for key, value in entry.new_state.items():
                        if hasattr(obj, key):
                            setattr(obj, key, value)
        elif entry.action == "clear":
            session.objects = []
        
        session.updated_at = datetime.utcnow()
        self._save_session(session_id)
        return True
    
    def can_undo(self, session_id: str) -> bool:
        """Check if undo is available"""
        history = self.histories.get(session_id)
        return history is not None and history.current_index >= 0
    
    def can_redo(self, session_id: str) -> bool:
        """Check if redo is available"""
        history = self.histories.get(session_id)
        return history is not None and history.current_index < len(history.entries) - 1
    
    # ═══════════════════════════════════════════════════════════════
    # AGENT COMMAND PROCESSING
    # ═══════════════════════════════════════════════════════════════
    
    def queue_agent_command(self, session_id: str, command: AgentDrawCommand):
        """Queue a command from an agent"""
        if session_id not in self.pending_commands:
            self.pending_commands[session_id] = []
        self.pending_commands[session_id].append(command)
    
    def get_pending_commands(self, session_id: str) -> List[AgentDrawCommand]:
        """Get and clear pending commands for a session"""
        commands = self.pending_commands.get(session_id, [])
        self.pending_commands[session_id] = []
        return commands
    
    async def process_agent_command(self, session_id: str, command: AgentDrawCommand) -> AgentCommandResponse:
        """Process a single agent command"""
        session = self.sessions.get(session_id)
        if not session:
            return AgentCommandResponse(
                command_id=command.id,
                status="error",
                error="Session not found"
            )
        
        try:
            result = {}
            
            if command.action == "set_mode" and command.mode:
                session.mode = command.mode
                result["mode"] = command.mode.value
            
            elif command.action == "clear":
                self.clear_objects(session_id)
                result["cleared"] = True
            
            elif command.action == "add_text" and command.text:
                obj = CanvasObject(
                    type="text",
                    text=command.text,
                    x=command.x or 100,
                    y=command.y or 100,
                    font_size=command.font_size or 16,
                    stroke_color=command.color or "#ffffff",
                    author_agent=command.agent_id,
                )
                self.add_object(session_id, obj)
                result["object_id"] = obj.id
            
            elif command.action == "add_shape" and command.shape_type:
                props = command.props or {}
                obj = CanvasObject(
                    type=command.shape_type,
                    author_agent=command.agent_id,
                    **props
                )
                self.add_object(session_id, obj)
                result["object_id"] = obj.id
            
            elif command.action == "draw":
                # Complex drawing commands handled by frontend
                # Just queue for frontend processing
                result["queued"] = True
            
            return AgentCommandResponse(
                command_id=command.id,
                status="success",
                result=result
            )
        
        except Exception as e:
            return AgentCommandResponse(
                command_id=command.id,
                status="error",
                error=str(e)
            )


# Global state manager instance
state_manager = CanvasStateManager()
