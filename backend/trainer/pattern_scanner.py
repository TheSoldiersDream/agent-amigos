"""
Pattern Scanner (AOB Scanner) - Find code signatures in memory
Standard game trainer feature for finding code locations via byte patterns
"""
from typing import List, Optional, Tuple
import re


class PatternMatch:
    def __init__(self, address: int, pattern: str):
        self.address = address
        self.pattern = pattern
    
    def __repr__(self):
        return f"PatternMatch(address={hex(self.address)}, pattern='{self.pattern}')"


def parse_pattern(pattern: str) -> Tuple[bytes, bytes]:
    """
    Parse AOB pattern string into bytes and mask
    
    Format: "48 8B ?? 24 ?? FF" where ?? is wildcard
    
    Returns:
        (pattern_bytes, mask_bytes) where mask has 0xFF for exact match, 0x00 for wildcard
    """
    parts = pattern.upper().replace(",", " ").split()
    pattern_bytes = bytearray()
    mask_bytes = bytearray()
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
        
        if part == "??" or part == "?":
            # Wildcard
            pattern_bytes.append(0x00)
            mask_bytes.append(0x00)
        else:
            # Exact byte
            try:
                byte_val = int(part, 16)
                pattern_bytes.append(byte_val)
                mask_bytes.append(0xFF)
            except ValueError:
                raise ValueError(f"Invalid byte value: {part}")
    
    return bytes(pattern_bytes), bytes(mask_bytes)


def scan_pattern(
    process_handle,
    pattern: str,
    start_address: Optional[int] = None,
    end_address: Optional[int] = None,
    first_only: bool = False
) -> List[PatternMatch]:
    """
    Scan for byte pattern in process memory
    
    Args:
        process_handle: Handle to target process
        pattern: Pattern string like "48 8B ?? 24 ?? FF"
        start_address: Start of scan range (None = all memory)
        end_address: End of scan range (None = all memory)
        first_only: Return after first match
    
    Returns:
        List of pattern matches
    """
    pattern_bytes, mask_bytes = parse_pattern(pattern)
    results = []
    
    if start_address is not None and end_address is not None:
        regions = [(start_address, end_address)]
    else:
        regions = _get_executable_regions(process_handle)
    
    for region_start, region_end in regions:
        matches = _scan_region(process_handle, region_start, region_end, pattern_bytes, mask_bytes)
        for match_addr in matches:
            results.append(PatternMatch(match_addr, pattern))
            if first_only:
                return results
    
    return results


def _get_executable_regions(process_handle) -> List[Tuple[int, int]]:
    """Get all executable memory regions"""
    regions = []
    try:
        import ctypes
        
        MEMORY_BASIC_INFORMATION = ctypes.c_ulonglong * 7
        mbi = MEMORY_BASIC_INFORMATION()
        address = 0
        
        while address < 0x7FFFFFFFFFFF:
            result = ctypes.windll.kernel32.VirtualQueryEx(
                process_handle, address, ctypes.byref(mbi), ctypes.sizeof(mbi)
            )
            if not result:
                break
            
            base = mbi[0]
            size = mbi[2]
            protect = mbi[4]
            
            # Check if executable (PAGE_EXECUTE = 0x10, PAGE_EXECUTE_READ = 0x20, etc.)
            if protect in [0x10, 0x20, 0x40, 0x80]:
                regions.append((base, base + size))
            
            address = base + size
            
    except Exception:
        pass
    
    return regions


def _scan_region(
    process_handle, 
    start: int, 
    end: int, 
    pattern: bytes, 
    mask: bytes
) -> List[int]:
    """Scan a memory region for pattern"""
    matches = []
    
    try:
        import ctypes
        
        size = end - start
        if size > 100 * 1024 * 1024:  # Limit to 100MB per region
            return matches
        
        buffer = ctypes.create_string_buffer(size)
        bytes_read = ctypes.c_size_t()
        
        success = ctypes.windll.kernel32.ReadProcessMemory(
            process_handle, start, buffer, size, ctypes.byref(bytes_read)
        )
        
        if not success:
            return matches
        
        # Scan buffer for pattern
        pattern_len = len(pattern)
        for i in range(bytes_read.value - pattern_len + 1):
            if _matches_pattern(buffer.raw[i:i+pattern_len], pattern, mask):
                matches.append(start + i)
        
    except Exception:
        pass
    
    return matches


def _matches_pattern(data: bytes, pattern: bytes, mask: bytes) -> bool:
    """Check if data matches pattern with mask"""
    for i in range(len(pattern)):
        if mask[i] == 0xFF and data[i] != pattern[i]:
            return False
    return True


def pattern_to_regex(pattern: str) -> str:
    """Convert AOB pattern to regex for text search"""
    parts = pattern.upper().replace(",", " ").split()
    regex_parts = []
    
    for part in parts:
        if part == "??" or part == "?":
            regex_parts.append(".")
        else:
            regex_parts.append(re.escape(chr(int(part, 16))))
    
    return "".join(regex_parts)
