import ctypes
from typing import Any, Dict, List, Optional

from .process_manager import get_attached_process, kernel32, PROCESS_QUERY_INFORMATION, PROCESS_VM_READ


PAGE_READWRITE = 0x04
MEM_COMMIT = 0x1000


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", ctypes.c_ulong),
        ("RegionSize", ctypes.c_size_t),
        ("State", ctypes.c_ulong),
        ("Protect", ctypes.c_ulong),
        ("Type", ctypes.c_ulong),
    ]


VirtualQueryEx = kernel32.VirtualQueryEx
VirtualQueryEx.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(MEMORY_BASIC_INFORMATION), ctypes.c_size_t]
VirtualQueryEx.restype = ctypes.c_size_t

ReadProcessMemory = kernel32.ReadProcessMemory


_last_scan_results: List[int] = []

_SCAN_TYPES = {
    "int": ctypes.c_int,
    "uint": ctypes.c_uint,
    "float": ctypes.c_float,
    "double": ctypes.c_double,
    "byte": ctypes.c_ubyte,
}


def _ensure_attached():
    proc = get_attached_process()
    if proc is None:
        raise RuntimeError("No process attached")
    return proc


def enumerate_memory_regions(max_regions: int = 2048) -> List[Dict[str, Any]]:
    """Return a coarse list of readable, committed memory regions.

    This is a best-effort enumeration used by scan helpers.
    """

    proc = _ensure_attached()
    regions: List[Dict[str, Any]] = []

    mbi = MEMORY_BASIC_INFORMATION()
    address = 0
    size_mbi = ctypes.sizeof(mbi)

    while len(regions) < max_regions:
        result = VirtualQueryEx(proc.handle, ctypes.c_void_p(address), ctypes.byref(mbi), size_mbi)
        if not result:
            break

        if mbi.State == MEM_COMMIT and (mbi.Protect & PAGE_READWRITE):
            regions.append({
                "base": ctypes.addressof(mbi) and int(mbi.BaseAddress),
                "size": int(mbi.RegionSize),
            })

        address = int(mbi.BaseAddress) + int(mbi.RegionSize)

    return regions


def _read_region(proc_handle: int, base: int, size: int) -> Optional[bytes]:
    buffer = (ctypes.c_char * size)()
    bytes_read = ctypes.c_size_t()
    success = ReadProcessMemory(proc_handle, ctypes.c_void_p(base), buffer, size, ctypes.byref(bytes_read))
    if not success or bytes_read.value == 0:
        return None
    return bytes(buffer[: bytes_read.value])


def scan_exact_value(value: Any, type: str) -> List[int]:
    """Exact-value scan across readable regions for basic primitive types."""

    proc = _ensure_attached()

    if type not in _SCAN_TYPES:
        raise ValueError(f"scan_exact_value unsupported type '{type}'")

    if value is None:
        raise ValueError("scan_value requires a numeric value")

    ctype_cls = _SCAN_TYPES[type]
    try:
        if type == "float" or type == "double":
            numeric = float(value)
        else:
            numeric = int(value)
    except (TypeError, ValueError):
        raise ValueError("scan_value must be numeric")

    target = ctype_cls(numeric)

    target_b = bytes(target)

    matches: List[int] = []

    for region in enumerate_memory_regions():
        base = region["base"]
        size = region["size"]
        data = _read_region(proc.handle, base, size)
        if not data:
            continue
        idx = data.find(target_b)
        while idx != -1:
            matches.append(base + idx)
            idx = data.find(target_b, idx + 1)

    global _last_scan_results
    _last_scan_results = matches
    return matches


def scan_next(mode: str, value: Optional[Any] = None, type: str = "int") -> List[int]:
    """Next-scan refinement stub.

    For now, only supports exact scans when a value is provided. Other modes
    return the last scan results (placeholder for future refinements).
    """

    mode = (mode or "").lower().strip()
    if mode in {"exact", "value"} and value is not None:
        return scan_exact_value(value, type)
    if mode == "increased":
        return scan_increased()
    if mode == "decreased":
        return scan_decreased()
    if mode == "changed":
        return scan_changed()
    if mode == "unchanged":
        return scan_unchanged()
    return _last_scan_results


# Change-based scans are intentionally stubbed for now but wired for future use.


def scan_unknown_value(start_filter: str = "any") -> List[int]:
    global _last_scan_results
    _last_scan_results = []
    return _last_scan_results


def scan_increased() -> List[int]:
    return _last_scan_results


def scan_decreased() -> List[int]:
    return _last_scan_results


def scan_changed() -> List[int]:
    return _last_scan_results


def scan_unchanged() -> List[int]:
    return _last_scan_results


def scan_pattern(pattern: str) -> List[int]:
    """Delegates to AoB pattern scanner where implemented.

    For now, this is a thin wrapper and returns previous scan results.
    """

    return _last_scan_results
