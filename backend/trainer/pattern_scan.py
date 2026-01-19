from typing import List, Tuple

from .process_manager import get_attached_process, kernel32
from .memory_scanner import enumerate_memory_regions, _read_region


def parse_pattern(pattern: str) -> Tuple[bytes, bytes]:
    """Parse an AoB pattern like "48 8B ?? ?? 89 0D ??" into (bytes, mask).

    mask byte 0xFF means "match", 0x00 means wildcard.
    """

    tokens = pattern.split()
    pattern_bytes = bytearray()
    mask = bytearray()

    for t in tokens:
        if t == "??" or t == "?":
            pattern_bytes.append(0)
            mask.append(0)
        else:
            pattern_bytes.append(int(t, 16))
            mask.append(0xFF)

    return bytes(pattern_bytes), bytes(mask)


def _find_pattern_in_data(data: bytes, pat: bytes, mask: bytes) -> List[int]:
    matches: List[int] = []
    plen = len(pat)
    dlen = len(data)

    for i in range(0, dlen - plen + 1):
        ok = True
        for j in range(plen):
            if mask[j] and data[i + j] != pat[j]:
                ok = False
                break
        if ok:
            matches.append(i)
    return matches


def find_pattern_in_module(module_name: str, pattern: str) -> List[int]:
    proc = get_attached_process()
    if proc is None:
        raise RuntimeError("No process attached")

    pat, mask = parse_pattern(pattern)
    matches_global: List[int] = []

    for region in enumerate_memory_regions():
        base = region["base"]
        size = region["size"]
        data = _read_region(proc.handle, base, size)
        if not data:
            continue

        local_matches = _find_pattern_in_data(data, pat, mask)
        for off in local_matches:
            matches_global.append(base + off)

    return matches_global
