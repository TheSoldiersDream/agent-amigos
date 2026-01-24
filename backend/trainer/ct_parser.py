"""
Cheat Engine Table (.CT) file parser and converter.
Converts Cheat Engine XML format to Agent Amigos JSON cheat table format.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Optional
import re


class CTEntry:
    """Represents a single cheat entry from a CT file."""
    
    def __init__(self):
        self.id: str = ""
        self.description: str = ""
        self.address: Optional[str] = None
        self.offsets: List[str] = []
        self.variable_type: str = "4 Bytes"
        self.script: Optional[str] = None
        self.hotkeys: List[Dict] = []
        self.color: Optional[str] = None
        self.is_script: bool = False
        self.children: List['CTEntry'] = []
        
    def to_dict(self):
        """Convert to Agent Amigos cheat format."""
        return {
            "description": self.description,
            "address": self.address,
            "offsets": self.offsets,
            "variable_type": self.variable_type,
            "script": self.script,
            "hotkeys": self.hotkeys,
            "color": self.color,
            "is_script": self.is_script
        }


def parse_variable_type(ce_type: str) -> str:
    """Map Cheat Engine variable types to our format."""
    type_map = {
        "4 Bytes": "int32",
        "Byte": "int8",
        "2 Bytes": "int16",
        "8 Bytes": "int64",
        "Float": "float",
        "Double": "double",
        "String": "string",
        "Array of byte": "bytes",
        "Auto Assembler Script": "script"
    }
    return type_map.get(ce_type, "int32")


def parse_hotkey(hotkey_elem) -> Optional[Dict]:
    """Parse Cheat Engine hotkey to our format."""
    try:
        action = hotkey_elem.find("Action")
        keys_elem = hotkey_elem.find("Keys")
        
        if action is None or keys_elem is None:
            return None
            
        # CE uses Windows virtual key codes
        key_codes = [int(k.text) for k in keys_elem.findall("Key")]
        
        # Convert key codes to string representation
        # Common codes: 17=Ctrl, 16=Shift, 18=Alt, 45=Insert, 46=Delete
        key_map = {
            17: "Ctrl", 16: "Shift", 18: "Alt",
            45: "Insert", 46: "Delete", 36: "Home",
            35: "End", 33: "PageUp", 34: "PageDown"
        }
        
        key_parts = []
        for code in key_codes:
            if code in key_map:
                key_parts.append(key_map[code])
            elif 48 <= code <= 57:  # Numbers
                key_parts.append(str(code - 48))
            elif 65 <= code <= 90:  # Letters
                key_parts.append(chr(code))
            elif 112 <= code <= 123:  # F1-F12
                key_parts.append(f"F{code - 111}")
        
        return {
            "action": action.text.lower(),
            "keys": "+".join(key_parts)
        }
    except:
        return None


def parse_cheat_entry(entry_elem) -> CTEntry:
    """Parse a single CheatEntry element."""
    ct_entry = CTEntry()
    
    # Basic fields
    id_elem = entry_elem.find("ID")
    if id_elem is not None:
        ct_entry.id = id_elem.text or ""
    
    desc_elem = entry_elem.find("Description")
    if desc_elem is not None:
        # Clean HTML entities
        desc = desc_elem.text or ""
        desc = desc.replace("&lt;", "<").replace("&gt;", ">")
        ct_entry.description = desc
    
    # Color
    color_elem = entry_elem.find("Color")
    if color_elem is not None:
        ct_entry.color = f"#{color_elem.text}"
    
    # Variable type
    vtype_elem = entry_elem.find("VariableType")
    if vtype_elem is not None:
        ce_type = vtype_elem.text or "4 Bytes"
        ct_entry.variable_type = parse_variable_type(ce_type)
        ct_entry.is_script = "Script" in ce_type
    
    # Address
    addr_elem = entry_elem.find("Address")
    if addr_elem is not None and addr_elem.text:
        ct_entry.address = addr_elem.text
    
    # Offsets (for pointer paths)
    offsets_elem = entry_elem.find("Offsets")
    if offsets_elem is not None:
        ct_entry.offsets = [
            offset.text for offset in offsets_elem.findall("Offset")
            if offset.text
        ]
    
    # Assembler Script
    script_elem = entry_elem.find("AssemblerScript")
    if script_elem is not None and script_elem.text:
        ct_entry.script = script_elem.text.strip()
    
    # Hotkeys
    hotkeys_elem = entry_elem.find("Hotkeys")
    if hotkeys_elem is not None:
        for hk in hotkeys_elem.findall("Hotkey"):
            parsed_hk = parse_hotkey(hk)
            if parsed_hk:
                ct_entry.hotkeys.append(parsed_hk)
    
    # Child entries
    children_elem = entry_elem.find("CheatEntries")
    if children_elem is not None:
        for child in children_elem.findall("CheatEntry"):
            ct_entry.children.append(parse_cheat_entry(child))
    
    return ct_entry


def flatten_entries(entry: CTEntry, parent_desc: str = "") -> List[Dict]:
    """Flatten nested entries into a list of cheats."""
    cheats = []
    
    # Build full description with parent context
    full_desc = entry.description
    if parent_desc and not entry.is_script:
        full_desc = f"{parent_desc} - {entry.description}"
    
    # Only add entries that have actual addresses or scripts
    if entry.address or entry.script:
        cheat = {
            "name": full_desc.strip(),
            "description": full_desc.strip(),
            "enabled": False,
            "value_type": entry.variable_type,
            "aob_pattern": None
        }
        
        # Add script if present
        if entry.script:
            cheat["script"] = entry.script
            cheat["is_script"] = True
            
            # Try to extract AOB pattern from script
            # Example: aobscan(my_aob, 48 8B 05 ?? ?? ?? ??)
            aob_match = re.search(r'aobscan\s*\(\s*\w+\s*,\s*([0-9A-Fa-f\s\?]+)\s*\)', entry.script)
            if aob_match:
                cheat["aob_pattern"] = aob_match.group(1).strip()
            # Alternately, some scripts use 'aobscanmodule'
            elif "aobscanmodule" in entry.script:
                aob_match = re.search(r'aobscanmodule\s*\(\s*\w+\s*,\s*[\w\.]+\s*,\s*([0-9A-Fa-f\s\?]+)\s*\)', entry.script)
                if aob_match:
                    cheat["aob_pattern"] = aob_match.group(1).strip()
        
        # Add address or pointer path
        if entry.offsets and entry.address:
            # Pointer-based address
            offsets_str = ",".join(entry.offsets)
            cheat["pointer_path"] = f"{entry.address},{offsets_str}"
            cheat["address"] = None
        elif entry.address:
            # Direct address
            try:
                # Try to parse as hex address
                if entry.address.startswith("0x") or entry.address.startswith("0X"):
                    cheat["address"] = int(entry.address, 16)
                else:
                    # Symbol name (like "player") - store as pointer_path if it looks like "module.exe"+offset
                    if "+" in entry.address or '"' in entry.address:
                        cheat["pointer_path"] = entry.address
                        cheat["address"] = None
                    else:
                        cheat["address"] = entry.address
                        cheat["is_symbol"] = True
            except:
                cheat["address"] = entry.address
                cheat["is_symbol"] = True
        
        # Add hotkeys
        if entry.hotkeys:
            cheat["hotkeys"] = entry.hotkeys
        
        # Add color for UI
        if entry.color:
            cheat["color"] = entry.color
        
        cheats.append(cheat)
    
    # Process children recursively
    for child in entry.children:
        # Use current description as parent for children
        parent_prefix = full_desc if not entry.is_script else parent_desc
        cheats.extend(flatten_entries(child, parent_prefix))
    
    return cheats


def parse_ct_file(file_path: str) -> Dict:
    """
    Parse a Cheat Engine .CT file and convert to our JSON format.
    
    Args:
        file_path: Path to the .CT file
        
    Returns:
        Dict with game_name, version, cheats list
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"CT file not found: {file_path}")
    
    # Parse XML
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
    except Exception as e:
        raise ValueError(f"Failed to parse CT file: {e}")
    
    # Extract game name from filename
    # Format: "COTA_Gates of Hell Ostfront_1.013.0_G25.CT"
    game_name = path.stem
    
    # Try to extract version from filename
    version_match = re.search(r'_(\d+\.\d+\.\d+)', game_name)
    version = version_match.group(1) if version_match else "unknown"
    
    # Clean up game name (remove version suffix)
    game_name_clean = re.sub(r'_\d+\.\d+\.\d+.*$', '', game_name)
    game_name_clean = game_name_clean.replace("_", " ")
    
    # Parse all cheat entries
    all_cheats = []
    entries_elem = root.find("CheatEntries")
    
    if entries_elem is not None:
        for entry_elem in entries_elem.findall("CheatEntry"):
            ct_entry = parse_cheat_entry(entry_elem)
            all_cheats.extend(flatten_entries(ct_entry))
    
    return {
        "game_name": game_name_clean,
        "version": version,
        "cheats": all_cheats,
        "imported_from": str(path.name),
        "total_cheats": len(all_cheats)
    }


def validate_ct_import(ct_data: Dict) -> List[str]:
    """
    Validate imported CT data and return list of warnings/issues.
    
    Args:
        ct_data: Parsed CT data
        
    Returns:
        List of warning messages
    """
    warnings = []
    
    # Check for scripts (require manual review)
    script_count = sum(1 for c in ct_data["cheats"] if c.get("is_script", False))
    if script_count > 0:
        warnings.append(f"{script_count} script-based cheats detected. These require game-specific implementation.")
    
    # Check for symbol addresses
    symbol_count = sum(1 for c in ct_data["cheats"] if c.get("is_symbol", False))
    if symbol_count > 0:
        warnings.append(f"{symbol_count} symbol-based addresses detected. These may need pointer scanning.")
    
    # Check for missing addresses
    no_addr_count = sum(1 for c in ct_data["cheats"] 
                        if not c.get("address") and not c.get("pointer_base") and not c.get("script"))
    if no_addr_count > 0:
        warnings.append(f"{no_addr_count} entries have no address or script.")
    
    return warnings
