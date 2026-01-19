from fastapi import APIRouter
import time
from typing import List, Dict, Any, Optional
import threading

class UIController:
    def __init__(self):
        self._events: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._last_poll = time.time()

    def add_event(self, event_type: str, data: Dict[str, Any]):
        """Add a UI event to the queue."""
        with self._lock:
            self._events.append({
                "type": event_type,
                "data": data,
                "timestamp": time.time()
            })
            # Keep queue size manageable
            if len(self._events) > 50:
                self._events.pop(0)

    def get_events(self, since: float = 0) -> List[Dict[str, Any]]:
        """Get events since a specific timestamp."""
        with self._lock:
            return [e for e in self._events if e["timestamp"] > since]

    def open_console(self, console_name: str):
        self.add_event("open_console", {"console": console_name})

    def close_console(self, console_name: str):
        self.add_event("close_console", {"console": console_name})

    def set_input(self, element_id: str, value: str):
        self.add_event("set_input", {"id": element_id, "value": value})

ui_controller = UIController()

router = APIRouter(prefix="/ui", tags=["ui"])

@router.get("/events")
def get_ui_events(since: float = 0):
    return {"events": ui_controller.get_events(since)}

@router.post("/command")
def post_ui_command(command: Dict[str, Any]):
    """Allow agents to directly inject UI commands."""
    ui_controller.add_event(command.get("type", "unknown"), command.get("data", {}))
    return {"status": "success"}
