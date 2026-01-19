"""
Game Trainer & Memory Editor Tools - World Class Implementation
Professional-grade memory scanning, editing, and game training functionality.
Supports: Real memory scanning, pointer scanning, AOB pattern matching, cheat tables.
"""

import os
import ctypes
from ctypes import wintypes
import struct
import threading
import time
import json
from datetime import datetime

import psutil


def _unsafe_tools_enabled() -> bool:
    """Return True only when explicitly opted-in to unsafe capabilities.

    This module contains process attachment + memory read/write features that can
    be misused for cheating/hacking. We keep it disabled by default.
    """
    return os.getenv("AMIGOS_ENABLE_UNSAFE_TOOLS", "").strip().lower() in {"1", "true", "yes", "on"}


class DisabledGameTrainer:
    """Safe stub that refuses unsafe operations.

    Provides the same attribute/method surface as the real GameTrainer via
    __getattr__ to avoid import-time crashes when the tool is registered.
    """

    def __init__(self, reason: str):
        self._reason = reason
        self.attached = False
        self.process_name = None
        self.process_id = None
        self.attached_process = None

    def _disabled(self, *args, **kwargs) -> dict:
        return {
            "success": False,
            "error": self._reason,
            "disabled": True,
        }

    def __getattr__(self, name):
        return self._disabled

# Windows API Constants
PROCESS_ALL_ACCESS = 0x1F0FFF
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
PROCESS_QUERY_INFORMATION = 0x0400

MEM_COMMIT = 0x1000
PAGE_READONLY = 0x02
PAGE_READWRITE = 0x04
PAGE_WRITECOPY = 0x08
PAGE_EXECUTE_READ = 0x20
PAGE_EXECUTE_READWRITE = 0x40
PAGE_EXECUTE_WRITECOPY = 0x80
PAGE_GUARD = 0x100

READABLE_PAGES = (PAGE_READONLY | PAGE_READWRITE | PAGE_WRITECOPY | 
                   PAGE_EXECUTE_READ | PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY)

class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wintypes.DWORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wintypes.DWORD),
        ("Protect", wintypes.DWORD),
        ("Type", wintypes.DWORD),
    ]

class SYSTEM_INFO(ctypes.Structure):
    _fields_ = [
        ("wProcessorArchitecture", wintypes.WORD),
        ("wReserved", wintypes.WORD),
        ("dwPageSize", wintypes.DWORD),
        ("lpMinimumApplicationAddress", ctypes.c_void_p),
        ("lpMaximumApplicationAddress", ctypes.c_void_p),
        ("dwActiveProcessorMask", ctypes.c_void_p),
        ("dwNumberOfProcessors", wintypes.DWORD),
        ("dwProcessorType", wintypes.DWORD),
        ("dwAllocationGranularity", wintypes.DWORD),
        ("wProcessorLevel", wintypes.WORD),
        ("wProcessorRevision", wintypes.WORD),
    ]

class MODULEENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("th32ModuleID", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("GlblcntUsage", wintypes.DWORD),
        ("ProccntUsage", wintypes.DWORD),
        ("modBaseAddr", ctypes.c_void_p),
        ("modBaseSize", wintypes.DWORD),
        ("hModule", wintypes.HMODULE),
        ("szModule", ctypes.c_char * 256),
        ("szExePath", ctypes.c_char * 260),
    ]

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
kernel32.ReadProcessMemory.restype = wintypes.BOOL
kernel32.WriteProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
kernel32.WriteProcessMemory.restype = wintypes.BOOL
kernel32.VirtualQueryEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.POINTER(MEMORY_BASIC_INFORMATION), ctypes.c_size_t]
kernel32.VirtualQueryEx.restype = ctypes.c_size_t
kernel32.GetSystemInfo.argtypes = [ctypes.POINTER(SYSTEM_INFO)]
kernel32.GetSystemInfo.restype = None
kernel32.VirtualProtectEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
kernel32.VirtualProtectEx.restype = wintypes.BOOL
kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
kernel32.Module32First.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32)]
kernel32.Module32First.restype = wintypes.BOOL
kernel32.Module32Next.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32)]
kernel32.Module32Next.restype = wintypes.BOOL

TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010

KNOWN_GAMES = {
    "steam.exe": "Steam", "csgo.exe": "CS:GO", "cs2.exe": "CS2", "dota2.exe": "Dota 2",
    "GTA5.exe": "GTA V", "GTAV.exe": "GTA V", "eldenring.exe": "Elden Ring",
    "darksouls3.exe": "Dark Souls 3", "witcher3.exe": "Witcher 3", "cyberpunk2077.exe": "Cyberpunk",
    "Fallout4.exe": "Fallout 4", "Skyrim.exe": "Skyrim", "SkyrimSE.exe": "Skyrim SE",
    "minecraft.exe": "Minecraft", "javaw.exe": "Minecraft Java", "Terraria.exe": "Terraria",
    "HollowKnight.exe": "Hollow Knight", "Celeste.exe": "Celeste", "Hades.exe": "Hades",
    "notepad.exe": "Notepad (Test)", "re4.exe": "RE4", "RocketLeague.exe": "Rocket League",
    "call_to_arms.exe": "Call to Arms", "cta.exe": "Call to Arms",
}


class GameTrainer:
    def __init__(self):
        self.process_handle = None
        self.process_id = None
        self.process_name = None
        self.attached = False
        self.scan_results = []
        self.scan_history = []
        self.last_scan_type = None
        self.frozen_values = {}
        self.freeze_thread = None
        self.freeze_running = False
        self.modules = {}
        self.base_address = 0
        self.cheat_tables = {}
        self.pointer_chains = {}
        self.mods_dir = os.path.expanduser("~/Documents/AgentAmigos/GameTrainer/Mods")
        self.backups_dir = os.path.expanduser("~/Documents/AgentAmigos/GameTrainer/Backups")
        self.sys_info = SYSTEM_INFO()
        kernel32.GetSystemInfo(ctypes.byref(self.sys_info))
        self.data_dir = os.path.expanduser("~/Documents/AgentAmigos/GameTrainer")
        self.tables_dir = os.path.join(self.data_dir, "CheatTables")
        for d in [self.data_dir, self.tables_dir, self.mods_dir, self.backups_dir]:
            os.makedirs(d, exist_ok=True)

    def find_game_window(self, title: str = None) -> dict:
        """Find game windows by title."""
        try:
            import ctypes.wintypes
            user32 = ctypes.windll.user32
            windows = []
            def enum_callback(hwnd, _):
                if user32.IsWindowVisible(hwnd):
                    length = user32.GetWindowTextLengthW(hwnd) + 1
                    buf = ctypes.create_unicode_buffer(length)
                    user32.GetWindowTextW(hwnd, buf, length)
                    win_title = buf.value
                    if win_title and (not title or title.lower() in win_title.lower()):
                        windows.append({"hwnd": hwnd, "title": win_title})
                return True
            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.c_void_p)
            user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
            return {"success": True, "windows": windows[:50]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_mod_template(self, game_name: str, mod_name: str, mod_type: str = "script") -> dict:
        """Create a mod template for a game."""
        try:
            game_dir = os.path.join(self.mods_dir, game_name.replace(" ", "_"))
            os.makedirs(game_dir, exist_ok=True)
            mod_path = os.path.join(game_dir, f"{mod_name.replace(' ', '_')}.py")
            template = f'''# Mod: {mod_name} for {game_name}
# Created: {datetime.now().isoformat()}

def activate():
    """Activate the mod."""
    pass

def deactivate():
    """Deactivate the mod."""
    pass
'''
            with open(mod_path, 'w') as f:
                f.write(template)
            return {"success": True, "path": mod_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_mod_files(self, game_name: str = None) -> dict:
        """List mod files for a game."""
        try:
            mods = []
            search_dir = os.path.join(self.mods_dir, game_name.replace(" ", "_")) if game_name else self.mods_dir
            if os.path.exists(search_dir):
                for root, dirs, files in os.walk(search_dir):
                    for f in files:
                        mods.append({"path": os.path.join(root, f), "name": f})
            return {"success": True, "mods": mods}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def backup_game_files(self, game_name: str, files: list) -> dict:
        """Backup game files before modding."""
        try:
            import shutil
            backup_dir = os.path.join(self.backups_dir, game_name.replace(" ", "_"), datetime.now().strftime("%Y%m%d_%H%M%S"))
            os.makedirs(backup_dir, exist_ok=True)
            backed_up = []
            for f in files:
                if os.path.exists(f):
                    dest = os.path.join(backup_dir, os.path.basename(f))
                    shutil.copy2(f, dest)
                    backed_up.append(dest)
            return {"success": True, "backup_dir": backup_dir, "files": backed_up}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def restore_game_files(self, backup_path: str, destination: str) -> dict:
        """Restore game files from backup."""
        try:
            import shutil
            if os.path.isdir(backup_path):
                for f in os.listdir(backup_path):
                    src = os.path.join(backup_path, f)
                    dst = os.path.join(destination, f)
                    shutil.copy2(src, dst)
            else:
                shutil.copy2(backup_path, destination)
            return {"success": True, "restored_to": destination}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def edit_game_config(self, config_path: str, changes: dict) -> dict:
        """Edit game configuration files."""
        try:
            import configparser
            if config_path.endswith('.ini'):
                config = configparser.ConfigParser()
                config.read(config_path)
                for section, values in changes.items():
                    if section not in config:
                        config[section] = {}
                    for key, val in values.items():
                        config[section][key] = str(val)
                with open(config_path, 'w') as f:
                    config.write(f)
            elif config_path.endswith('.json'):
                with open(config_path, 'r') as f:
                    data = json.load(f)
                data.update(changes)
                with open(config_path, 'w') as f:
                    json.dump(data, f, indent=2)
            return {"success": True, "path": config_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_game_processes(self) -> dict:
        try:
            games, others = [], []
            # Build lowercase lookup
            known_lower = {k.lower(): v for k, v in KNOWN_GAMES.items()}
            for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                try:
                    info = proc.info
                    mem = info['memory_info'].rss / (1024*1024) if info['memory_info'] else 0
                    entry = {"pid": info['pid'], "name": info['name'], "memory_mb": round(mem, 2)}
                    proc_lower = info['name'].lower()
                    if proc_lower in known_lower:
                        entry["game_name"] = known_lower[proc_lower]
                        games.append(entry)
                    elif mem > 100:
                        others.append(entry)
                except: continue
            return {"success": True, "games": sorted(games, key=lambda x: x['memory_mb'], reverse=True),
                    "potential_games": sorted(others, key=lambda x: x['memory_mb'], reverse=True)[:20],
                    "attached": self.attached, "attached_to": self.process_name}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def attach_to_process(self, pid: int = None, name: str = None) -> dict:
        try:
            if self.attached: self.detach_from_process()
            target_pid, target_name = None, None
            if pid:
                target_pid = pid
                target_name = psutil.Process(pid).name()
            elif name:
                for p in psutil.process_iter(['pid', 'name']):
                    if name.lower() in p.info['name'].lower():
                        target_pid, target_name = p.info['pid'], p.info['name']
                        break
            if not target_pid:
                return {"success": False, "error": "Process not found"}
            self.process_handle = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, target_pid)
            if not self.process_handle:
                return {"success": False, "error": f"Failed to open process. Run as Admin. Error: {ctypes.get_last_error()}"}
            self.process_id, self.process_name, self.attached = target_pid, target_name, True
            self._enumerate_modules()
            self._start_freeze_thread()
            return {"success": True, "message": f"Attached to {target_name} (PID: {target_pid})",
                    "pid": target_pid, "base_address": hex(self.base_address) if self.base_address else "0x0"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def detach_from_process(self) -> dict:
        self._stop_freeze_thread()
        if self.process_handle: kernel32.CloseHandle(self.process_handle)
        old = self.process_name
        self.process_handle = self.process_id = self.process_name = None
        self.attached = False
        self.scan_results, self.modules, self.frozen_values = [], {}, {}
        return {"success": True, "message": f"Detached from {old}"}

    def _enumerate_modules(self):
        if not self.attached: return
        self.modules = {}
        snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, self.process_id)
        if snap == -1: return
        try:
            me = MODULEENTRY32()
            me.dwSize = ctypes.sizeof(MODULEENTRY32)
            if kernel32.Module32First(snap, ctypes.byref(me)):
                while True:
                    name = me.szModule.decode('utf-8', errors='ignore')
                    self.modules[name] = {"base": me.modBaseAddr, "size": me.modBaseSize}
                    if not self.base_address: self.base_address = me.modBaseAddr
                    if not kernel32.Module32Next(snap, ctypes.byref(me)): break
        finally:
            kernel32.CloseHandle(snap)

    def get_modules(self) -> dict:
        if not self.attached: return {"success": False, "error": "Not attached"}
        return {"success": True, "modules": [{
            "name": n, "base": hex(i["base"]) if i["base"] else "0x0", "size": i["size"]
        } for n, i in self.modules.items()]}

    def read_memory(self, address: int, size: int = 4, data_type: str = "int") -> dict:
        if not self.attached: return {"success": False, "error": "Not attached"}
        try:
            buf = ctypes.create_string_buffer(size)
            read = ctypes.c_size_t()
            if not kernel32.ReadProcessMemory(self.process_handle, ctypes.c_void_p(address), buf, size, ctypes.byref(read)):
                return {"success": False, "error": f"Read failed: {ctypes.get_last_error()}"}
            raw = buf.raw[:read.value]
            fmt = {'int': '<i', 'uint': '<I', 'short': '<h', 'ushort': '<H', 'byte': '<B',
                   'float': '<f', 'double': '<d', 'long': '<q', 'ulong': '<Q'}
            val = struct.unpack(fmt.get(data_type, '<i'), raw)[0] if data_type in fmt else raw.hex()
            return {"success": True, "address": hex(address), "value": val, "hex": raw.hex()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def write_memory(self, address: int, value, data_type: str = "int") -> dict:
        if not self.attached: return {"success": False, "error": "Not attached"}
        try:
            fmt = {'int': '<i', 'uint': '<I', 'short': '<h', 'ushort': '<H', 'byte': '<B',
                   'float': '<f', 'double': '<d', 'long': '<q', 'ulong': '<Q'}
            if data_type == "bytes":
                buf = bytes.fromhex(value.replace(" ", "")) if isinstance(value, str) else bytes(value)
            elif data_type in fmt:
                buf = struct.pack(fmt[data_type], float(value) if 'float' in data_type or 'double' in data_type else int(value))
            else:
                return {"success": False, "error": f"Unknown type: {data_type}"}
            old = wintypes.DWORD()
            kernel32.VirtualProtectEx(self.process_handle, ctypes.c_void_p(address), len(buf), PAGE_EXECUTE_READWRITE, ctypes.byref(old))
            written = ctypes.c_size_t()
            res = kernel32.WriteProcessMemory(self.process_handle, ctypes.c_void_p(address), buf, len(buf), ctypes.byref(written))
            kernel32.VirtualProtectEx(self.process_handle, ctypes.c_void_p(address), len(buf), old.value, ctypes.byref(old))
            if not res: return {"success": False, "error": f"Write failed: {ctypes.get_last_error()}"}
            return {"success": True, "address": hex(address), "written": written.value}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_memory_regions(self) -> list:
        regions = []
        addr = self.sys_info.lpMinimumApplicationAddress
        max_addr = self.sys_info.lpMaximumApplicationAddress
        mbi = MEMORY_BASIC_INFORMATION()
        while addr < max_addr:
            if kernel32.VirtualQueryEx(self.process_handle, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)) == 0:
                break
            if mbi.State == MEM_COMMIT and (mbi.Protect & READABLE_PAGES) and not (mbi.Protect & PAGE_GUARD):
                regions.append({"base": mbi.BaseAddress, "size": mbi.RegionSize})
            addr = mbi.BaseAddress + mbi.RegionSize
        return regions

    def scan_memory_for_value(self, value, data_type: str = "int", scan_type: str = "exact") -> dict:
        if not self.attached: return {"success": False, "error": "Not attached"}
        try:
            sizes = {"byte": 1, "short": 2, "ushort": 2, "int": 4, "uint": 4, "float": 4, "long": 8, "ulong": 8, "double": 8}
            vsize = sizes.get(data_type, 4)
            fmt = {'int': '<i', 'uint': '<I', 'short': '<h', 'ushort': '<H', 'byte': '<B', 'float': '<f', 'double': '<d', 'long': '<q', 'ulong': '<Q'}
            search = struct.pack(fmt.get(data_type, '<i'), float(value) if 'float' in data_type or 'double' in data_type else int(value))
            results, scanned = [], 0
            for region in self._get_memory_regions():
                try:
                    buf = ctypes.create_string_buffer(region["size"])
                    read = ctypes.c_size_t()
                    if not kernel32.ReadProcessMemory(self.process_handle, ctypes.c_void_p(region["base"]), buf, region["size"], ctypes.byref(read)):
                        continue
                    scanned += read.value
                    data = buf.raw[:read.value]
                    if scan_type == "exact":
                        off = 0
                        while True:
                            pos = data.find(search, off)
                            if pos == -1: break
                            results.append({"address": region["base"] + pos, "value": value, "data_type": data_type})
                            off = pos + 1
                            if len(results) >= 50000: break
                except: continue
                if len(results) >= 50000: break
            self.scan_results, self.last_scan_type = results, data_type
            self.scan_history.append({"time": datetime.now().isoformat(), "value": value, "count": len(results)})
            return {"success": True, "count": len(results), "results": results[:100], "scanned_mb": round(scanned/(1024*1024), 2)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def next_scan(self, new_value, scan_type: str = "exact") -> dict:
        if not self.attached: return {"success": False, "error": "Not attached"}
        if not self.scan_results: return {"success": False, "error": "No previous scan"}
        try:
            new_results = []
            for entry in self.scan_results:
                cur = self.read_memory(entry["address"], 4, self.last_scan_type)
                if not cur["success"]: continue
                cv, ov = cur["value"], entry["value"]
                match = (scan_type == "exact" and cv == new_value) or \
                        (scan_type == "changed" and cv != ov) or \
                        (scan_type == "unchanged" and cv == ov) or \
                        (scan_type == "increased" and cv > ov) or \
                        (scan_type == "decreased" and cv < ov)
                if match:
                    new_results.append({"address": entry["address"], "value": cv, "previous": ov, "data_type": self.last_scan_type})
            self.scan_results = new_results
            return {"success": True, "count": len(new_results), "results": new_results[:100]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_scan_results(self, limit: int = 100) -> dict:
        """Get current scan results."""
        if not self.attached:
            return {"success": False, "error": "Not attached to any process"}
        return {
            "success": True,
            "count": len(self.scan_results),
            "results": [
                {"address": r["address"], "value": r["value"], "data_type": r.get("data_type", self.last_scan_type or "int")}
                for r in self.scan_results[:limit]
            ]
        }

    def aob_scan(self, pattern: str, module: str = None) -> dict:
        if not self.attached: return {"success": False, "error": "Not attached"}
        try:
            parts = pattern.upper().split()
            search, mask = [], []
            for p in parts:
                if p in ("??", "?"):
                    search.append(0); mask.append(False)
                else:
                    search.append(int(p, 16)); mask.append(True)
            results = []
            regions = [{"base": self.modules[module]["base"], "size": self.modules[module]["size"]}] if module and module in self.modules else self._get_memory_regions()
            for region in regions:
                try:
                    buf = ctypes.create_string_buffer(region["size"])
                    read = ctypes.c_size_t()
                    if not kernel32.ReadProcessMemory(self.process_handle, ctypes.c_void_p(region["base"]), buf, region["size"], ctypes.byref(read)):
                        continue
                    data = buf.raw[:read.value]
                    for i in range(len(data) - len(search) + 1):
                        if all(not m or data[i+j] == s for j, (s, m) in enumerate(zip(search, mask))):
                            results.append({"address": region["base"] + i, "bytes": ' '.join(f'{b:02X}' for b in data[i:i+len(search)])})
                            if len(results) >= 1000: break
                except: continue
                if len(results) >= 1000: break
            return {"success": True, "pattern": pattern, "count": len(results), "results": results[:50]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def pointer_scan(self, target_address: int, max_offset: int = 0x1000) -> dict:
        if not self.attached: return {"success": False, "error": "Not attached"}
        try:
            results = []
            ptr_size = ctypes.sizeof(ctypes.c_void_p)
            tmin, tmax = target_address - max_offset, target_address + max_offset
            for region in self._get_memory_regions():
                if region["size"] > 50*1024*1024: continue
                try:
                    buf = ctypes.create_string_buffer(region["size"])
                    read = ctypes.c_size_t()
                    if not kernel32.ReadProcessMemory(self.process_handle, ctypes.c_void_p(region["base"]), buf, region["size"], ctypes.byref(read)):
                        continue
                    data = buf.raw[:read.value]
                    for i in range(0, len(data) - ptr_size + 1, ptr_size):
                        pv = struct.unpack('<Q' if ptr_size == 8 else '<I', data[i:i+ptr_size])[0]
                        if tmin <= pv <= tmax:
                            addr = region["base"] + i
                            mod = next((n for n, m in self.modules.items() if m["base"] <= addr < m["base"] + m["size"]), None)
                            results.append({"ptr_addr": hex(addr), "points_to": hex(pv), "offset": hex(target_address - pv), "module": mod})
                            if len(results) >= 500: break
                except: continue
                if len(results) >= 500: break
            results.sort(key=lambda x: (x["module"] is None, abs(int(x["offset"], 16))))
            return {"success": True, "target": hex(target_address), "count": len(results), "results": results[:50]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _start_freeze_thread(self):
        if self.freeze_thread and self.freeze_thread.is_alive(): return
        self.freeze_running = True
        self.freeze_thread = threading.Thread(target=self._freeze_loop, daemon=True)
        self.freeze_thread.start()

    def _stop_freeze_thread(self):
        self.freeze_running = False
        if self.freeze_thread: self.freeze_thread.join(timeout=1)

    def _freeze_loop(self):
        while self.freeze_running and self.attached:
            for addr, info in list(self.frozen_values.items()):
                if not self.attached: break
                self.write_memory(int(addr, 16), info["value"], info["type"])
            time.sleep(0.05)

    def freeze_value(self, address: int, value, data_type: str = "int", name: str = None) -> dict:
        if not self.attached: return {"success": False, "error": "Not attached"}
        res = self.write_memory(address, value, data_type)
        if not res["success"]: return res
        self.frozen_values[hex(address)] = {"value": value, "type": data_type, "name": name or f"Value_{len(self.frozen_values)+1}"}
        return {"success": True, "message": f"Frozen {hex(address)} to {value}", "frozen_count": len(self.frozen_values)}

    def unfreeze_value(self, address: int) -> dict:
        addr = hex(address)
        if addr in self.frozen_values:
            del self.frozen_values[addr]
            return {"success": True, "message": f"Unfrozen {addr}"}
        return {"success": False, "error": "Not frozen"}

    def unfreeze_all(self) -> dict:
        c = len(self.frozen_values)
        self.frozen_values = {}
        return {"success": True, "message": f"Unfroze {c} values"}

    def list_frozen_values(self) -> dict:
        return {"success": True, "frozen": self.frozen_values, "count": len(self.frozen_values)}

    def save_cheat_table(self, name: str, description: str = "") -> dict:
        try:
            table = {"name": name, "desc": description, "process": self.process_name, "created": datetime.now().isoformat(),
                     "entries": [{"addr": hex(r["address"]), "val": r["value"], "type": r.get("data_type", "int")} for r in self.scan_results[:100]],
                     "frozen": dict(self.frozen_values)}
            path = os.path.join(self.tables_dir, f"{name.replace(' ', '_')}.json")
            with open(path, 'w') as f: json.dump(table, f, indent=2)
            return {"success": True, "path": path, "entries": len(table["entries"])}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def load_cheat_table(self, name: str) -> dict:
        try:
            for f in os.listdir(self.tables_dir):
                if f.startswith(name.replace(' ', '_')) and f.endswith('.json'):
                    with open(os.path.join(self.tables_dir, f)) as fp:
                        table = json.load(fp)
                    self.cheat_tables[name] = table
                    return {"success": True, "table": table}
            return {"success": False, "error": "Not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_cheat_tables(self) -> dict:
        try:
            tables = []
            for f in os.listdir(self.tables_dir):
                if f.endswith('.json'):
                    with open(os.path.join(self.tables_dir, f)) as fp:
                        t = json.load(fp)
                    tables.append({"name": t.get("name", f), "process": t.get("process"), "entries": len(t.get("entries", []))})
            return {"success": True, "tables": tables}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def apply_cheat_table(self, name: str) -> dict:
        if name not in self.cheat_tables:
            res = self.load_cheat_table(name)
            if not res["success"]: return res
        table = self.cheat_tables[name]
        applied = 0
        for addr, info in table.get("frozen", {}).items():
            if self.freeze_value(int(addr, 16), info["value"], info["type"])["success"]:
                applied += 1
        return {"success": True, "applied": applied}

    def get_status(self) -> dict:
        return {"attached": self.attached, "process": self.process_name, "pid": self.process_id,
                "base": hex(self.base_address) if self.base_address else None, "modules": len(self.modules),
                "results": len(self.scan_results), "frozen": len(self.frozen_values)}

    def nop_instruction(self, address: int, length: int = 1) -> dict:
        return self.write_memory(address, "90" * length, "bytes")

    def dump_memory(self, address: int, size: int, path: str = None) -> dict:
        if not self.attached: return {"success": False, "error": "Not attached"}
        try:
            buf = ctypes.create_string_buffer(size)
            read = ctypes.c_size_t()
            if not kernel32.ReadProcessMemory(self.process_handle, ctypes.c_void_p(address), buf, size, ctypes.byref(read)):
                return {"success": False, "error": "Read failed"}
            if not path: path = os.path.join(self.data_dir, f"dump_{hex(address)}_{size}.bin")
            with open(path, 'wb') as f: f.write(buf.raw[:read.value])
            return {"success": True, "path": path, "bytes": read.value}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def game_trainer_help(self) -> dict:
        return {"success": True, "help": {
            "workflow": ["1. list_game_processes()", "2. attach_to_process(pid=...)", "3. scan_memory_for_value(100)",
                         "4. Change value in game", "5. next_scan(new_value)", "6. write_memory(addr, 999)", "7. freeze_value(addr, 999)"],
            "features": ["Real Memory Scanning", "Next Scan Filtering", "AOB Pattern Scan", "Pointer Scanning",
                         "Value Freezing", "Cheat Tables", "Memory Dump", "NOP Patching"],
            "types": ["byte", "short", "ushort", "int", "uint", "float", "double", "long", "ulong"],
            "scan_types": {"first": ["exact", "greater", "less"], "next": ["exact", "changed", "unchanged", "increased", "decreased"]}
        }}


_DISABLED_REASON = (
    "Game Trainer tools are disabled by default because they can be used for cheating/hacking. "
    "If you are doing authorized debugging/QA in your own environment, set AMIGOS_ENABLE_UNSAFE_TOOLS=true to enable."
)

trainer = GameTrainer() if _unsafe_tools_enabled() else DisabledGameTrainer(_DISABLED_REASON)

# Compatibility properties
if not hasattr(trainer, "attached_process"):
    trainer.attached_process = None

def list_game_processes() -> dict: return trainer.list_game_processes()
def attach_to_process(pid: int = None, name: str = None) -> dict: return trainer.attach_to_process(pid, name)
def detach_from_process() -> dict: return trainer.detach_from_process()
def get_modules() -> dict: return trainer.get_modules()
def read_memory(address: int, size: int = 4, data_type: str = "int") -> dict: return trainer.read_memory(address, size, data_type)
def write_memory(address: int, value, data_type: str = "int") -> dict: return trainer.write_memory(address, value, data_type)
def scan_memory(value, data_type: str = "int", scan_type: str = "exact") -> dict: return trainer.scan_memory_for_value(value, data_type, scan_type)
def scan_memory_for_value(value, data_type: str = "int", scan_type: str = "exact") -> dict: return trainer.scan_memory_for_value(value, data_type, scan_type)
def get_scan_results(limit: int = 100) -> dict: return trainer.get_scan_results(limit)
def next_scan(new_value, scan_type: str = "exact") -> dict: return trainer.next_scan(new_value, scan_type)
def aob_scan(pattern: str, module: str = None) -> dict: return trainer.aob_scan(pattern, module)
def pointer_scan(target_address: int, max_offset: int = 0x1000) -> dict: return trainer.pointer_scan(target_address, max_offset)
def freeze_value(address: int, value, data_type: str = "int", name: str = None) -> dict: return trainer.freeze_value(address, value, data_type, name)
def unfreeze_value(address: int) -> dict: return trainer.unfreeze_value(address)
def unfreeze_all() -> dict: return trainer.unfreeze_all()
def list_frozen_values() -> dict: return trainer.list_frozen_values()
def save_cheat_table(name: str, description: str = "") -> dict: return trainer.save_cheat_table(name, description)
def load_cheat_table(name: str) -> dict: return trainer.load_cheat_table(name)
def list_cheat_tables() -> dict: return trainer.list_cheat_tables()
def apply_cheat_table(name: str) -> dict: return trainer.apply_cheat_table(name)
def get_trainer_status() -> dict: return trainer.get_status()
def nop_instruction(address: int, length: int = 1) -> dict: return trainer.nop_instruction(address, length)
def dump_memory(address: int, size: int, path: str = None) -> dict: return trainer.dump_memory(address, size, path)
def game_trainer_help() -> dict: return trainer.game_trainer_help()
def find_game_window(title: str = None) -> dict: return trainer.find_game_window(title)
def create_mod_template(game_name: str, mod_name: str, mod_type: str = "script") -> dict: return trainer.create_mod_template(game_name, mod_name, mod_type)
def list_mod_files(game_name: str = None) -> dict: return trainer.list_mod_files(game_name)
def backup_game_files(game_name: str, files: list) -> dict: return trainer.backup_game_files(game_name, files)
def restore_game_files(backup_path: str, destination: str) -> dict: return trainer.restore_game_files(backup_path, destination)
def edit_game_config(config_path: str, changes: dict) -> dict: return trainer.edit_game_config(config_path, changes)
