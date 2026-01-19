import ctypes
from typing import Any, Dict, Optional

from .process_manager import get_attached_process, PROCESS_VM_READ, PROCESS_VM_WRITE, PROCESS_VM_OPERATION, kernel32


TYPE_SIZES = {
    "int": ctypes.c_int,
    "uint": ctypes.c_uint,
    "float": ctypes.c_float,
    "double": ctypes.c_double,
}


def _ensure_attached():
    proc = get_attached_process()
    if proc is None:
        raise RuntimeError("No process attached")
    return proc


def _resolve_ctype(type_name: str):
    if type_name not in TYPE_SIZES:
        raise ValueError(f"Unsupported type: {type_name}")
    return TYPE_SIZES[type_name]


def read_memory(address: int, type: str) -> Dict[str, Any]:
    proc = _ensure_attached()
    ctype_cls = _resolve_ctype(type)
    buffer = ctype_cls()
    bytes_read = ctypes.c_size_t()

    success = kernel32.ReadProcessMemory(
        proc.handle,
        ctypes.c_void_p(address),
        ctypes.byref(buffer),
        ctypes.sizeof(buffer),
        ctypes.byref(bytes_read),
    )

    if not success:
        raise OSError(f"ReadProcessMemory failed at 0x{address:X}")

    return {"address": address, "type": type, "value": buffer.value}


def write_memory(address: int, type: str, new_value: Any) -> Dict[str, Any]:
    proc = _ensure_attached()
    ctype_cls = _resolve_ctype(type)
    buffer = ctype_cls(new_value)
    bytes_written = ctypes.c_size_t()

    success = kernel32.WriteProcessMemory(
        proc.handle,
        ctypes.c_void_p(address),
        ctypes.byref(buffer),
        ctypes.sizeof(buffer),
        ctypes.byref(bytes_written),
    )

    if not success:
        raise OSError(f"WriteProcessMemory failed at 0x{address:X}")

    return {"address": address, "type": type, "value": new_value}


_frozen_values: Dict[int, Dict[str, Any]] = {}


def freeze_memory(address: int, type: str, value: Any, interval_ms: int = 100):
    """Record a frozen memory value.

    The trainer engine is responsible for periodically re-applying freezes
    using this registry.
    """

    _frozen_values[address] = {
        "type": type,
        "value": value,
        "interval_ms": interval_ms,
    }
    return {"address": address, "type": type, "value": value, "interval_ms": interval_ms}


def unfreeze_memory(address: int):
    _frozen_values.pop(address, None)
    return {"address": address, "unfrozen": True}


def get_frozen_registry() -> Dict[int, Dict[str, Any]]:
    return _frozen_values
