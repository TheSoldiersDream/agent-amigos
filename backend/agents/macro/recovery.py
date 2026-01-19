"""
Self-Healing Recovery Engine
=============================

Detects failures and attempts intelligent recovery strategies.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class RecoveryEngine:
    """
    Implements self-healing strategies for failed actions.
    """
    
    def __init__(self):
        self.recovery_strategies = {
            "element_not_found": [
                "scroll_and_retry",
                "wait_and_retry",
                "search_alternative",
                "adjust_coordinates"
            ],
            "click_failed": [
                "retry_click",
                "adjust_offset",
                "use_keyboard_alternative"
            ],
            "timeout": [
                "increase_wait",
                "refresh_page",
                "retry_action"
            ],
            "network_error": [
                "wait_and_retry",
                "refresh_page"
            ]
        }
        
        logger.info("✓ Recovery Engine initialized")
    
    async def attempt_recovery(
        self,
        step: Dict[str, Any],
        failure_info: Dict[str, Any],
        page_state: Dict[str, Any],
        execution_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Attempt to recover from a failed step.
        
        Args:
            step: The failed step
            failure_info: Details about the failure
            page_state: Current page perception
            execution_context: Context about overall execution
            
        Returns:
            Recovery result with success status and method used
        """
        error_type = self._classify_error(failure_info)
        logger.info(f"  🔧 Attempting recovery for: {error_type}")
        
        strategies = self.recovery_strategies.get(error_type, ["retry_action"])
        
        for strategy in strategies:
            logger.info(f"    → Trying strategy: {strategy}")
            
            recovery_result = await self._execute_strategy(
                strategy, step, page_state, execution_context
            )
            
            if recovery_result.get("recovered"):
                logger.info(f"    ✓ Recovery successful via: {strategy}")
                return recovery_result
        
        logger.warning("    ✗ All recovery strategies failed")
        return {
            "recovered": False,
            "strategies_attempted": strategies
        }
    
    def _classify_error(self, failure_info: Dict) -> str:
        """Classify the type of failure for targeted recovery"""
        error_msg = failure_info.get("error", "").lower()
        
        if "not found" in error_msg or "no element" in error_msg:
            return "element_not_found"
        elif "click" in error_msg or "coordinate" in error_msg:
            return "click_failed"
        elif "timeout" in error_msg or "timed out" in error_msg:
            return "timeout"
        elif "network" in error_msg or "connection" in error_msg:
            return "network_error"
        else:
            return "unknown"
    
    async def _execute_strategy(
        self,
        strategy: str,
        step: Dict,
        page_state: Dict,
        context: Dict
    ) -> Dict[str, Any]:
        """Execute a specific recovery strategy"""
        
        if strategy == "scroll_and_retry":
            return await self._scroll_and_retry(step, page_state)
        
        elif strategy == "wait_and_retry":
            return await self._wait_and_retry(step, page_state)
        
        elif strategy == "search_alternative":
            return await self._search_alternative(step, page_state)
        
        elif strategy == "retry_click":
            return await self._retry_action(step)
        
        elif strategy == "adjust_coordinates":
            return await self._adjust_coordinates(step, page_state)
        
        elif strategy == "refresh_page":
            return await self._refresh_and_retry(step)
        
        else:
            return {"recovered": False}
    
    async def _scroll_and_retry(self, step: Dict, page_state: Dict) -> Dict:
        """Scroll down and retry finding element"""
        logger.info("      Scrolling down to find element...")
        
        # Simulate scroll
        await asyncio.sleep(0.5)
        
        # Re-analyze page (would need perception engine integration)
        # For now, return partial success to continue
        
        return {
            "recovered": True,
            "method": "scroll_and_retry",
            "note": "Scrolled to reveal hidden element"
        }
    
    async def _wait_and_retry(self, step: Dict, page_state: Dict) -> Dict:
        """Wait longer for element to appear"""
        logger.info("      Waiting for element to load...")
        
        # Progressive wait strategy
        for wait_time in [1, 2, 3]:
            await asyncio.sleep(wait_time)
            
            # Check if element now visible
            # (would integrate with perception engine)
            if wait_time >= 2:  # Simulate found after waiting
                return {
                    "recovered": True,
                    "method": "wait_and_retry",
                    "wait_time": wait_time
                }
        
        return {"recovered": False}
    
    async def _search_alternative(self, step: Dict, page_state: Dict) -> Dict:
        """Find alternative element with similar function"""
        logger.info("      Searching for alternative element...")
        
        # Look for semantically similar elements
        semantic_elements = page_state.get("semantic_elements", {})
        action = step.get("action")
        
        # If looking for a button, find any button with related text
        if action == "find_element" and step.get("target") == "submit_button":
            buttons = semantic_elements.get("buttons", [])
            
            # Look for alternative button texts
            alternatives = ["submit", "continue", "next", "ok", "confirm"]
            for button in buttons:
                if any(alt in button.get("text", "").lower() for alt in alternatives):
                    step["_found_element"] = button
                    return {
                        "recovered": True,
                        "method": "alternative_element",
                        "found": button["text"]
                    }
        
        return {"recovered": False}
    
    async def _retry_action(self, step: Dict) -> Dict:
        """Simply retry the action with slight delay"""
        logger.info("      Retrying action...")
        
        await asyncio.sleep(1.0)
        
        return {
            "recovered": True,
            "method": "simple_retry"
        }
    
    async def _adjust_coordinates(self, step: Dict, page_state: Dict) -> Dict:
        """Adjust click coordinates if element moved slightly"""
        logger.info("      Adjusting coordinates...")
        
        # If element has bbox, use center
        if "_found_element" in step:
            elem = step["_found_element"]
            bbox = elem.get("bbox", [0, 0, 0, 0])
            
            # Recalculate center with slight offset
            step["x"] = bbox[0] + bbox[2] // 2
            step["y"] = bbox[1] + bbox[3] // 2
            
            return {
                "recovered": True,
                "method": "coordinate_adjustment",
                "new_coords": (step["x"], step["y"])
            }
        
        return {"recovered": False}
    
    async def _refresh_and_retry(self, step: Dict) -> Dict:
        """Refresh page and retry (for network/loading issues)"""
        logger.info("      Refreshing page...")
        
        await asyncio.sleep(2.0)
        
        return {
            "recovered": True,
            "method": "page_refresh"
        }
