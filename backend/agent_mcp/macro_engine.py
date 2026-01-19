import json
import os
import time
import uuid
from datetime import datetime

class MacroEngine:
    def __init__(self, base_path="agent_mcp/macros"):
        self.base_path = base_path
        self.user_generated_path = os.path.join(base_path, "user_generated")
        self.ai_suggested_path = os.path.join(base_path, "ai_suggested")
        self.trusted_path = os.path.join(base_path, "trusted")
        self.logs = []
        
        # Ensure directories exist
        os.makedirs(self.user_generated_path, exist_ok=True)
        os.makedirs(self.ai_suggested_path, exist_ok=True)
        os.makedirs(self.trusted_path, exist_ok=True)

    def log_action(self, agent, action, context=None):
        """Logs a user action for pattern recognition."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": agent,
            "action": action,
            "context": context or {}
        }
        self.logs.append(entry)
        # In a real system, we might persist this log to a file or DB
        # For now, we keep it in memory or append to a daily log file
        return entry

    def detect_patterns(self):
        """
        Analyzes logs to find repeated sequences.
        This is a simplified implementation.
        """
        # TODO: Implement N-gram analysis or similar pattern matching
        # For now, return a dummy pattern if we have enough logs
        if len(self.logs) > 5:
            return [{
                "pattern_id": "sample_pattern",
                "confidence": 0.5,
                "occurrences": 1,
                "steps": self.logs[-3:] # Last 3 steps
            }]
        return []

    def create_macro(self, name, steps, trigger=None, category="user_generated"):
        """Creates and saves a new macro."""
        macro_id = str(uuid.uuid4())
        macro_data = {
            "id": macro_id,
            "name": name,
            "trigger": trigger,
            "steps": steps,
            "created_at": datetime.now().isoformat(),
            "category": category,
            "permissions": ["default"] # TODO: Infer permissions
        }
        
        target_dir = getattr(self, f"{category}_path", self.user_generated_path)
        file_path = os.path.join(target_dir, f"{macro_id}.json")
        
        with open(file_path, 'w') as f:
            json.dump(macro_data, f, indent=2)
            
        return macro_id

    def list_macros(self):
        """Lists all available macros."""
        macros = []
        for category in ["user_generated", "ai_suggested", "trusted"]:
            path = getattr(self, f"{category}_path")
            if os.path.exists(path):
                for filename in os.listdir(path):
                    if filename.endswith(".json"):
                        try:
                            with open(os.path.join(path, filename), 'r') as f:
                                macro = json.load(f)
                                macro["source"] = category
                                macros.append(macro)
                        except Exception as e:
                            print(f"Error loading macro {filename}: {e}")
        return macros

    def get_macro(self, macro_id):
        """Retrieves a specific macro by ID."""
        for macro in self.list_macros():
            if macro["id"] == macro_id:
                return macro
        return None

    def execute_macro(self, macro_id, executor_func):
        """
        Executes a macro using the provided executor function.
        executor_func(tool, params) -> result
        """
        macro = self.get_macro(macro_id)
        if not macro:
            return {"success": False, "error": "Macro not found"}
            
        results = []
        for step in macro["steps"]:
            # step should be {"tool": "...", "params": {...}}
            tool = step.get("tool")
            params = step.get("params", {})
            
            try:
                result = executor_func(tool, params)
                results.append({"step": step, "result": result, "success": True})
            except Exception as e:
                results.append({"step": step, "error": str(e), "success": False})
                # Stop on failure?
                break
                
        return {"success": True, "results": results}
