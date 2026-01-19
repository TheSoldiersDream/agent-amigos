import ctypes
import ctypes.wintypes as wintypes
from typing import List, Optional, Dict, Any

import psutil


PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008


kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


class AttachedProcess:
    """Represents an attached game process.

    This is a lightweight wrapper used by other trainer modules.
    """

    def __init__(self, pid: int, handle: int, name: str):
        self.pid = pid
        self.handle = handle
        self.name = name


_attached_process: Optional[AttachedProcess] = None


def get_attached_process() -> Optional[AttachedProcess]:
    return _attached_process


def list_processes() -> List[Dict[str, Any]]:
    """Return a list of running processes (pid, name, exe, memory_mb).

    This intentionally returns a small info subset for the UI.
    """

    processes: List[Dict[str, Any]] = []
    for proc in psutil.process_iter(["pid", "name", "exe", "memory_info"]):
        info = proc.info
        exe_path = info.get("exe") or ""
        memory_mb = None
        mem_info = info.get("memory_info")
        if mem_info is not None:
            try:
                memory_mb = round(mem_info.rss / (1024 * 1024), 1)
            except Exception:
                memory_mb = None
        is_steam_game = "steamapps" in (exe_path or "").lower()
        processes.append(
            {
                "pid": info.get("pid"),
                "name": info.get("name") or "",
                "exe": exe_path,
                "memory_mb": memory_mb,
                "is_steam_game": is_steam_game,
            }
        )
    return processes


def _open_process(pid: int) -> int:
    access = PROCESS_QUERY_INFORMATION | PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION
    handle = kernel32.OpenProcess(access, False, pid)
    if not handle:
        raise OSError(f"Failed to open process {pid}: {ctypes.get_last_error()}")
    return handle


def attach_to_process(process_name: str) -> Optional[AttachedProcess]:
    """Attach to a process by executable name.

    Returns AttachedProcess on success, or None if not found.
    """

    global _attached_process

    candidates = [
        p for p in psutil.process_iter(["pid", "name"]) if (p.info.get("name") or "").lower() == process_name.lower()
    ]
    if not candidates:
        return None

    proc = candidates[0]
    handle = _open_process(proc.pid)
    _attached_process = AttachedProcess(pid=proc.pid, handle=handle, name=proc.info.get("name") or "")
    return _attached_process


def attach_to_pid(pid: int) -> Optional[AttachedProcess]:
    """Attach to a process by PID."""

    global _attached_process

    try:
        proc = psutil.Process(int(pid))
    except Exception:
        return None

    try:
        handle = _open_process(proc.pid)
    except Exception:
        return None

    _attached_process = AttachedProcess(pid=proc.pid, handle=handle, name=proc.name() or "")
    return _attached_process


def detach_process() -> bool:
    """Detach from any currently attached process."""

    global _attached_process
    if _attached_process is None:
        return False
    try:
        kernel32.CloseHandle(_attached_process.handle)
    except Exception:
        pass
    _attached_process = None
    return True


def get_modules() -> List[Dict[str, Any]]:
    """Return loaded modules for the attached process (best-effort).

    Uses psutil's memory_maps as a cross-version approximation.
    """

    if _attached_process is None:
        return []

    try:
        p = psutil.Process(_attached_process.pid)
        modules = []
        for m in p.memory_maps():
            modules.append({"path": m.path, "addr": m.addr, "rss": m.rss})
        return modules
    except Exception:
        return []


def get_module_base(name: str) -> Optional[int]:
    """Return base address of a module whose path ends with name.

    This is a heuristic helper for pattern and pointer scans.
    """

    if _attached_process is None:
        return None

    try:
        p = psutil.Process(_attached_process.pid)
        for m in p.memory_maps():
            if m.path and m.path.lower().endswith(name.lower()):
                # psutil reports addr as string on some versions ("0x1234-0x5678").
                addr_str = str(m.addr)
                if "-" in addr_str:
                    start, _ = addr_str.split("-", 1)
                    return int(start, 16)
                try:
                    return int(addr_str, 16)
                except ValueError:
                    continue
    except Exception:
        return None

    return None
