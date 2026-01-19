"""Utility runner for declarative browser actions via Playwright."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BrowserActionExecutor:
    """Executes a narrow set of scripted actions against a Playwright page."""

    async def run(self, page: Any, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        log: List[Dict[str, Any]] = []
        for index, action in enumerate(actions, start=1):
            action_type = action.get("type")
            entry: Dict[str, Any] = {
                "index": index,
                "type": action_type,
                "success": False,
            }
            try:
                if action_type == "click":
                    await page.click(action["selector"], timeout=int(action.get("timeout", 10000)))
                elif action_type == "type":
                    await page.fill(action["selector"], action.get("value", ""))
                    if action.get("press_enter"):
                        await page.press(action["selector"], "Enter")
                elif action_type == "wait_for_selector":
                    await page.wait_for_selector(action["selector"], timeout=int(action.get("timeout", 10000)))
                elif action_type == "wait":
                    await asyncio.sleep(float(action.get("seconds", 1.0)))
                elif action_type == "scroll":
                    await page.mouse.wheel(0, int(action.get("amount", 0)))
                elif action_type == "screenshot":
                    await page.screenshot(path=action["path"], full_page=True)
                    entry["path"] = action["path"]
                else:
                    entry["error"] = f"Unsupported action: {action_type}"
                    log.append(entry)
                    continue
                entry["success"] = True
            except Exception as exc:
                entry["error"] = str(exc)
                logger.warning("Browser action failed (%s): %s", action_type, exc)
            log.append(entry)
        return log
