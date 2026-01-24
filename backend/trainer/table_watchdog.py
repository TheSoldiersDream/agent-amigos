
import os
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from . import process_manager
from .cheat_manager import get_cheat_manager, CheatTable, Cheat
from .pattern_scanner import scan_pattern
from .pointer_scanner import parse_pointer_path, resolve_pointer_chain
from .memory_writer import read_memory

logger = logging.getLogger(__name__)

class TableWatchdog:
    """
    Monitors attached process and manages cheat table synchronization, 
    auto-loading, and self-fixing of broken pointers.
    """
    
    def __init__(self):
        self.manager = get_cheat_manager()
        self.current_table: Optional[CheatTable] = None
        self.last_fix_attempt: Dict[str, datetime] = {}

    def auto_attach_table(self) -> Optional[CheatTable]:
        """
        Attempts to find and load a cheat table for the currently attached process.
        """
        proc = process_manager.get_attached_process()
        if not proc:
            return None
        
        # Look for matching table by exact name or fuzzy name
        tables = self.manager.list_tables()
        match_name = None
        
        # Clean process name (e.g. game.exe -> game)
        clean_proc = proc.name.lower().replace(".exe", "")
        
        for t in tables:
            if t.lower() == clean_proc or clean_proc in t.lower() or t.lower() in clean_proc:
                match_name = t
                break
        
        if match_name:
            logger.info(f"Auto-loading cheat table for: {match_name}")
            self.current_table = self.manager.load_table(match_name)
            return self.current_table
        
        return None

    def validate_and_fix_table(self, table: CheatTable) -> Dict[str, Any]:
        """
        Iterates through cheats and attempts to fix invalid addresses using AOBs or pointers.
        """
        proc = process_manager.get_attached_process()
        if not proc:
            return {"success": False, "error": "No process attached"}
        
        fix_results = {
            "total": len(table.cheats),
            "fixed": 0,
            "broken": 0,
            "valid": 0,
            "details": []
        }

        updated = False
        
        for cheat in table.cheats:
            status = self._check_cheat_validity(cheat)
            
            if status == "valid":
                fix_results["valid"] += 1
                cheat.validation_status = "valid"
                continue
            
            # Try to fix
            new_address = self._attempt_fix(cheat)
            if new_address:
                logger.info(f"Fixed cheat '{cheat.name}': {hex(cheat.address or 0)} -> {hex(new_address)}")
                cheat.address = new_address
                cheat.validation_status = "valid"
                fix_results["fixed"] += 1
                updated = True
                fix_results["details"].append({"name": cheat.name, "status": "fixed", "new_address": hex(new_address)})
            else:
                cheat.validation_status = "broken"
                fix_results["broken"] += 1
                fix_results["details"].append({"name": cheat.name, "status": "broken"})

        if updated:
            self.manager.save_table(table)
            
        return fix_results

    def _check_cheat_validity(self, cheat: Cheat) -> str:
        """
        Checks if the current address points to data that makes sense.
        """
        if not cheat.address:
            return "invalid"
            
        try:
            val = read_memory(cheat.address, cheat.value_type)
            if val and val.get("value") is not None:
                # Basic sanity check: if it's 0 or -1 it might still be valid, 
                # but if we can't read it, it's definitely invalid.
                return "valid"
        except:
            pass
            
        return "invalid"

    def _attempt_fix(self, cheat: Cheat) -> Optional[int]:
        """
        Tries to find a new address for the cheat using AOB or Pointer Path.
        """
        proc = process_manager.get_attached_process()
        if not proc:
            return None

        # 1. Try AOB Pattern if available
        if cheat.aob_pattern:
            matches = scan_pattern(proc.handle, cheat.aob_pattern, first_only=True)
            if matches:
                return matches[0].address

        # 2. Try Pointer Path if available
        if cheat.pointer_path:
            try:
                # Need to handle module base if pointer path contains it
                # Format usually: "game.exe"+0x123,0x44,0x55
                path_data = parse_pointer_path(cheat.pointer_path)
                if path_data:
                    base_module = path_data.get("module")
                    base_addr = 0
                    if base_module:
                        base_addr = process_manager.get_module_base(base_module) or 0
                    
                    final_addr = resolve_pointer_chain(proc.handle, base_addr + path_data["offset"], path_data["offsets"])
                    if final_addr:
                        return final_addr
            except Exception as e:
                logger.error(f"Failed to resolve pointer for {cheat.name}: {e}")

        return None

# Global instance
_watchdog = TableWatchdog()

def get_watchdog() -> TableWatchdog:
    return _watchdog
