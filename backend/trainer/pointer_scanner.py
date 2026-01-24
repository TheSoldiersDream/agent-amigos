"""
Pointer Scanner - Find static pointers to dynamic addresses
Standard game trainer feature for finding permanent memory addresses
"""
from typing import List, Dict, Any, Optional, Set
import struct


class PointerScanResult:
    def __init__(self, base_address: int, offsets: List[int], final_value: Any):
        self.base_address = base_address
        self.offsets = offsets
        self.final_value = final_value
        self.path = f"[{hex(base_address)}]" + "".join(f" + {hex(o)}" for o in offsets)


def scan_pointers(
    process_handle,
    target_address: int,
    max_offset: int = 0x1000,
    max_depth: int = 5,
    scan_range: Optional[tuple] = None
) -> List[PointerScanResult]:
    """
    Find static pointers that lead to target_address
    
    Args:
        process_handle: Handle to target process
        target_address: Address we want to find pointers to
        max_offset: Maximum offset to check at each level
        max_depth: Maximum pointer chain depth
        scan_range: (start, end) memory range to scan, None for all
    
    Returns:
        List of pointer paths that resolve to target_address
    """
    results = []
    
    # Get memory regions to scan
    if scan_range:
        regions = [scan_range]
    else:
        regions = _get_readable_regions(process_handle)
    
    # Level 1: Direct pointers
    for region_start, region_end in regions:
        pointers = _find_direct_pointers(process_handle, region_start, region_end, target_address)
        for ptr_addr in pointers:
            results.append(PointerScanResult(ptr_addr, [], target_address))
    
    # Recursive pointer chains (multi-level)
    if max_depth > 1:
        checked: Set[int] = set()
        for depth in range(1, max_depth):
            new_targets = [r.base_address for r in results if len(r.offsets) == depth - 1]
            for target in new_targets:
                if target in checked:
                    continue
                checked.add(target)
                
                for region_start, region_end in regions:
                    pointers = _find_direct_pointers(process_handle, region_start, region_end, target)
                    for ptr_addr in pointers:
                        # Try offsets
                        for offset in range(0, max_offset, 4):
                            test_result = PointerScanResult(ptr_addr, [offset], target_address)
                            if _validate_pointer_path(process_handle, test_result):
                                results.append(test_result)
    
    return results


def _get_readable_regions(process_handle) -> List[tuple]:
    """Get all readable memory regions"""
    regions = []
    try:
        import ctypes
        from ctypes import wintypes
        
        MEMORY_BASIC_INFORMATION = ctypes.c_ulonglong * 7
        mbi = MEMORY_BASIC_INFORMATION()
        address = 0
        
        while True:
            result = ctypes.windll.kernel32.VirtualQueryEx(
                process_handle, address, ctypes.byref(mbi), ctypes.sizeof(mbi)
            )
            if not result:
                break
            
            base = mbi[0]
            size = mbi[2]
            protect = mbi[4]
            
            # Check if readable (PAGE_READONLY = 2, PAGE_READWRITE = 4)
            if protect in [2, 4, 0x20, 0x40]:
                regions.append((base, base + size))
            
            address = base + size
            
    except Exception:
        pass
    
    return regions


def _find_direct_pointers(process_handle, start: int, end: int, target_address: int) -> List[int]:
    """Find addresses that point directly to target_address"""
    pointers = []
    try:
        import ctypes
        
        # Read memory region
        size = end - start
        buffer = ctypes.create_string_buffer(size)
        bytes_read = ctypes.c_size_t()
        
        success = ctypes.windll.kernel32.ReadProcessMemory(
            process_handle, start, buffer, size, ctypes.byref(bytes_read)
        )
        
        if not success:
            return pointers
        
        # Scan for target address as pointer value
        for i in range(0, bytes_read.value - 8, 8):  # 8-byte aligned scan
            try:
                value = struct.unpack("<Q", buffer.raw[i:i+8])[0]
                if value == target_address:
                    pointers.append(start + i)
            except struct.error:
                continue
                
    except Exception:
        pass
    
    return pointers


def _validate_pointer_path(process_handle, result: PointerScanResult) -> bool:
    """Verify that pointer path resolves correctly"""
    try:
        import ctypes
        
        current_addr = result.base_address
        
        for offset in result.offsets:
            # Read pointer at current address
            buffer = ctypes.c_ulonglong()
            bytes_read = ctypes.c_size_t()
            
            success = ctypes.windll.kernel32.ReadProcessMemory(
                process_handle, current_addr, ctypes.byref(buffer), 8, ctypes.byref(bytes_read)
            )
            
            if not success or bytes_read.value != 8:
                return False
            
            current_addr = buffer.value + offset
        
        # Final address should match target
        return current_addr == result.final_value
        
    except Exception:
        return False


def format_pointer_path(result: PointerScanResult) -> str:
    """Format pointer path for display"""
    if not result.offsets:
        return f"[{hex(result.base_address)}]"
    
    path = f"[[{hex(result.base_address)}]"
    for offset in result.offsets:
        if offset > 0:
            path += f" + {hex(offset)}"
        else:
            path += f" - {hex(-offset)}"
    path += "]"
    
    return path


def parse_pointer_path(path: str) -> Optional[Dict[str, Any]]:
    """
    Parse a pointer path string like '"game.exe"+0x123,0x44,0x55' or '0x1000,0x44'
    Returns: {module: str, offset: int, offsets: List[int]}
    """
    if not path:
        return None
        
    try:
        # Check for module name
        import re
        module_match = re.search(r'["\']?([^"\']+\.exe|[^"\']+\.dll)["\']?\s*\+\s*(0x[0-9a-fA-F]+|[0-9]+)', path)
        
        module = None
        base_offset = 0
        offsets = []
        
        if module_match:
            module = module_match.group(1)
            base_offset = int(module_match.group(2), 16) if module_match.group(2).startswith("0x") else int(module_match.group(2))
            # Get the rest of the offsets
            remaining = path[module_match.end():]
            offset_matches = re.findall(r',\s*(0x[0-9a-fA-F]+|[0-9]+)', remaining)
            offsets = [int(o, 16) if o.startswith("0x") else int(o) for o in offset_matches]
        else:
            # Simple comma separated list
            parts = [p.strip() for p in path.split(",")]
            if parts:
                base_offset = int(parts[0], 16) if parts[0].startswith("0x") else int(parts[0])
                if len(parts) > 1:
                    offsets = [int(o, 16) if o.startswith("0x") else int(o) for o in parts[1:]]
        
        return {
            "module": module,
            "offset": base_offset,
            "offsets": offsets
        }
    except Exception:
        return None


def resolve_pointer_chain(process_handle, base_addr: int, offsets: List[int]) -> Optional[int]:
    """
    Resolve a pointer chain starting at base_addr with given offsets.
    """
    import ctypes
    current_addr = base_addr
    
    try:
        for offset in offsets:
            buffer = ctypes.c_uint64()
            bytes_read = ctypes.c_size_t()
            success = ctypes.windll.kernel32.ReadProcessMemory(
                process_handle, current_addr, ctypes.byref(buffer), 8, ctypes.byref(bytes_read)
            )
            if not success or bytes_read.value != 8:
                return None
            current_addr = buffer.value + offset
            
        return current_addr
    except Exception:
        return None
