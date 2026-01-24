"""
Cheat Management System - Save/load/manage cheats
Standard trainer feature for persistent cheat configurations
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import os


class Cheat:
    def __init__(
        self,
        name: str,
        description: str,
        address: Optional[int] = None,
        pointer_path: Optional[str] = None,
        aob_pattern: Optional[str] = None,
        value_type: str = "int",
        frozen_value: Any = None,
        hotkey: Optional[str] = None,
        enabled: bool = False,
        increment: Optional[float] = None,
    ):
        self.name = name
        self.description = description
        self.address = address
        self.pointer_path = pointer_path
        self.aob_pattern = aob_pattern
        self.value_type = value_type
        self.frozen_value = frozen_value
        self.hotkey = hotkey
        self.enabled = enabled
        self.increment = increment
        self.created_at = datetime.utcnow().isoformat()
        self.validation_status = "unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "address": self.address,
            "pointer_path": self.pointer_path,
            "aob_pattern": self.aob_pattern,
            "value_type": self.value_type,
            "frozen_value": self.frozen_value,
            "hotkey": self.hotkey,
            "enabled": self.enabled,
            "increment": self.increment,
            "created_at": self.created_at,
            "validation_status": self.validation_status,
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Cheat":
        cheat = Cheat(
            name=data.get("name", "Unknown"),
            description=data.get("description", ""),
            address=data.get("address"),
            pointer_path=data.get("pointer_path"),
            aob_pattern=data.get("aob_pattern"),
            value_type=data.get("value_type", "int"),
            frozen_value=data.get("frozen_value"),
            hotkey=data.get("hotkey"),
            enabled=data.get("enabled", False),
            increment=data.get("increment"),
        )
        cheat.created_at = data.get("created_at", cheat.created_at)
        cheat.validation_status = data.get("validation_status", "unknown")
        return cheat


class CheatTable:
    def __init__(self, game_name: str):
        self.game_name = game_name
        self.cheats: List[Cheat] = []
        self.created_at = datetime.utcnow().isoformat()
        self.modified_at = datetime.utcnow().isoformat()
    
    def add_cheat(self, cheat: Cheat):
        self.cheats.append(cheat)
        self.modified_at = datetime.utcnow().isoformat()
    
    def remove_cheat(self, name: str) -> bool:
        original_len = len(self.cheats)
        self.cheats = [c for c in self.cheats if c.name != name]
        if len(self.cheats) < original_len:
            self.modified_at = datetime.utcnow().isoformat()
            return True
        return False
    
    def get_cheat(self, name: str) -> Optional[Cheat]:
        for cheat in self.cheats:
            if cheat.name == name:
                return cheat
        return None
    
    def update_cheat(self, name: str, updates: Dict[str, Any]) -> bool:
        cheat = self.get_cheat(name)
        if not cheat:
            return False
        
        for key, value in updates.items():
            if hasattr(cheat, key):
                setattr(cheat, key, value)
        
        self.modified_at = datetime.utcnow().isoformat()
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "game_name": self.game_name,
            "cheats": [c.to_dict() for c in self.cheats],
            "created_at": self.created_at,
            "modified_at": self.modified_at,
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "CheatTable":
        table = CheatTable(data.get("game_name", "Unknown"))
        table.cheats = [Cheat.from_dict(c) for c in data.get("cheats", [])]
        table.created_at = data.get("created_at", table.created_at)
        table.modified_at = data.get("modified_at", table.modified_at)
        return table


class CheatTableManager:
    def __init__(self, storage_dir: str = "trainer_data/cheat_tables"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
    
    def _get_table_path(self, game_name: str) -> str:
        # Sanitize filename
        safe_name = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in game_name)
        safe_name = safe_name.strip().replace(" ", "_").lower()
        return os.path.join(self.storage_dir, f"{safe_name}.json")
    
    def save_table(self, table: CheatTable) -> bool:
        try:
            path = self._get_table_path(table.game_name)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(table.to_dict(), f, indent=2)
            return True
        except Exception as e:
            print(f"Failed to save cheat table: {e}")
            return False
    
    def load_table(self, game_name: str) -> Optional[CheatTable]:
        try:
            path = self._get_table_path(game_name)
            if not os.path.exists(path):
                return None
            
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            return CheatTable.from_dict(data)
        except Exception as e:
            print(f"Failed to load cheat table: {e}")
            return None
    
    def list_tables(self) -> List[str]:
        try:
            files = os.listdir(self.storage_dir)
            return [f.replace(".json", "").replace("_", " ").title() for f in files if f.endswith(".json")]
        except Exception:
            return []
    
    def delete_table(self, game_name: str) -> bool:
        try:
            path = self._get_table_path(game_name)
            if os.path.exists(path):
                os.remove(path)
                return True
            return False
        except Exception:
            return False


# Global instance
_cheat_manager = CheatTableManager()


def get_cheat_manager() -> CheatTableManager:
    return _cheat_manager
