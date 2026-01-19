"""Safe Window Management Tools (Windows)

These tools support UI automation workflows (e.g., game-playing assistant) without
process attachment or memory manipulation.

They are intentionally kept separate from `game_tools.py`, which contains unsafe
capabilities gated behind AMIGOS_ENABLE_UNSAFE_TOOLS.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import ctypes
import ctypes.wintypes


def _get_window_text(hwnd: int) -> str:
    try:
        user32 = ctypes.windll.user32
        length = user32.GetWindowTextLengthW(ctypes.wintypes.HWND(hwnd))
        if length <= 0:
            return ""
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(ctypes.wintypes.HWND(hwnd), buf, length + 1)
        return buf.value or ""
    except Exception:
        return ""


def list_windows(title_contains: Optional[str] = None, visible_only: bool = True, limit: int = 50) -> Dict[str, Any]:
    """List top-level windows.

    Args:
        title_contains: Optional case-insensitive substring filter.
        visible_only: If True, only return visible windows.
        limit: Maximum returned windows.
    """
    try:
        user32 = ctypes.windll.user32
        results: List[Dict[str, Any]] = []
        title_filter = (title_contains or "").strip().lower()

        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.c_void_p)

        def enum_cb(hwnd, _lparam):
            try:
                if visible_only and not user32.IsWindowVisible(hwnd):
                    return True
                title = _get_window_text(int(hwnd))
                if not title:
                    return True
                if title_filter and title_filter not in title.lower():
                    return True
                results.append({"hwnd": int(hwnd), "title": title})
                if limit and len(results) >= int(limit):
                    return False
                return True
            except Exception:
                return True

        user32.EnumWindows(EnumWindowsProc(enum_cb), 0)
        return {"success": True, "windows": results, "count": len(results)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_foreground_window() -> Dict[str, Any]:
    """Get the current foreground window."""
    try:
        user32 = ctypes.windll.user32
        hwnd = int(user32.GetForegroundWindow())
        title = _get_window_text(hwnd)
        return {"success": True, "hwnd": hwnd, "title": title}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_window_rect(hwnd: int) -> Dict[str, Any]:
    """Get window rectangle (screen coordinates) suitable for screenshot region.

    Returns left/top/width/height.
    """
    try:
        user32 = ctypes.windll.user32

        rect = ctypes.wintypes.RECT()
        ok = user32.GetWindowRect(ctypes.wintypes.HWND(int(hwnd)), ctypes.byref(rect))
        if not ok:
            return {"success": False, "error": "GetWindowRect failed"}

        left = int(rect.left)
        top = int(rect.top)
        right = int(rect.right)
        bottom = int(rect.bottom)
        width = max(0, right - left)
        height = max(0, bottom - top)

        return {
            "success": True,
            "hwnd": int(hwnd),
            "left": left,
            "top": top,
            "width": width,
            "height": height,
            "right": right,
            "bottom": bottom,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def activate_window(hwnd: int) -> Dict[str, Any]:
    """Attempt to bring a window to the foreground.

    Note: Windows may restrict SetForegroundWindow depending on focus rules.
    """
    try:
        user32 = ctypes.windll.user32
        hwnd_i = int(hwnd)

        # Restore if minimized
        SW_RESTORE = 9
        user32.ShowWindow(ctypes.wintypes.HWND(hwnd_i), SW_RESTORE)

        ok = bool(user32.SetForegroundWindow(ctypes.wintypes.HWND(hwnd_i)))
        return {"success": True, "hwnd": hwnd_i, "set_foreground": ok, "title": _get_window_text(hwnd_i)}
    except Exception as e:
        return {"success": False, "error": str(e)}
