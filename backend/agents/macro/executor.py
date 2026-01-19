"""
Adaptive Execution Engine
==========================

Executes macro steps with human-like behavior:
- Natural mouse movement curves
- Variable typing speeds
- Scroll inertia
- Focus awareness
"""

import logging
import asyncio
import time
import math
import random
from typing import Dict, Any, Optional, Tuple

try:
    import pyautogui
    import pyperclip
    AUTOMATION_AVAILABLE = True
except ImportError:
    AUTOMATION_AVAILABLE = False

logger = logging.getLogger(__name__)


class MacroExecutor:
    """
    Executes macro steps with intelligent, adaptive behavior.
    """
    
    def __init__(self):
        self.paused = False
        self.stopped = False
        self.current_step = None
        
        # Human-like behavior settings
        self.typing_speed_base = 0.08  # seconds per character
        self.typing_speed_variance = 0.04
        self.mouse_speed_base = 0.3  # seconds for movement
        self.mouse_curve_points = 10  # Bezier curve smoothness
        
        if AUTOMATION_AVAILABLE:
            pyautogui.FAILSAFE = True  # Move to corner to abort
            pyautogui.PAUSE = 0.1
        
        logger.info(f"✓ Macro Executor initialized (PyAutoGUI: {AUTOMATION_AVAILABLE})")
    
    async def execute_step(
        self,
        step: Dict[str, Any],
        page_state: Dict[str, Any],
        page: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Execute a single macro step with adaptive behavior.
        
        Args:
            step: Step definition from planner
            page_state: Current perception of page
            
        Returns:
            Execution result with success status and details
        """
        self.current_step = step
        action = step.get("action")
        
        logger.info(f"  → Executing: {action}")
        
        # Check pause/stop flags
        while self.paused and not self.stopped:
            await asyncio.sleep(0.1)
        
        if self.stopped:
            return {"success": False, "error": "Execution stopped by user"}
        
        # Route to appropriate handler
        try:
            if action == "find_element":
                return await self._execute_find_element(step, page_state)
            elif action == "click":
                return await self._execute_click(step, page_state, page=page)
            elif action == "type_text":
                return await self._execute_type(step, page_state, page=page)
            elif action == "press_key":
                return await self._execute_key_press(step, page=page)
            elif action == "scroll":
                return await self._execute_scroll(step, page=page)
            elif action == "navigate":
                return await self._execute_navigate(step, page=page)
            elif action == "screenshot":
                return await self._execute_screenshot(step, page=page)
            elif action in ["wait", "wait_for_results", "wait_for_page"]:
                return await self._execute_wait(step)
            elif action == "verify_completion":
                return await self._execute_verify(step, page_state)
            else:
                logger.warning(f"⚠ Unknown action: {action}")
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            logger.error(f"✗ Step execution failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def _execute_find_element(
        self,
        step: Dict,
        page_state: Dict
    ) -> Dict[str, Any]:
        """Find an element using perception engine"""
        target = step.get("target")
        selectors = step.get("selectors", {})
        
        # Extract hints from selectors
        visual_hints = selectors.get("visual_hints", [])
        visual_hints.extend(selectors.get("button_text", []))
        visual_hints.extend(selectors.get("link_text", []))
        visual_hints.extend(selectors.get("aria_labels", []))
        
        # Search in page_state semantic elements
        element_found = None
        
        for category in ["buttons", "inputs", "links"]:
            elements = page_state.get("semantic_elements", {}).get(category, [])
            for elem in elements:
                elem_text = elem.get("text", "").lower()
                if any(hint.lower() in elem_text for hint in visual_hints):
                    element_found = elem
                    break
            if element_found:
                break
        
        if element_found:
            # Store for next action
            step["_found_element"] = element_found
            return {
                "success": True,
                "element": element_found,
                "method": "visual_semantic"
            }
        else:
            return {
                "success": False,
                "error": f"Element not found: {target}"
            }
    
    async def _execute_click(
        self,
        step: Dict,
        page_state: Dict,
        page: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Execute click with Playwright or PyAutoGUI"""
        if page:
            try:
                # Try to find refined selector from DOM data
                target = step.get("target")
                selector = None
                
                # If we have a found element with an ID or unique class
                if "_found_element" in step:
                    elem = step["_found_element"]
                    if elem.get("id"):
                        selector = f"#{elem['id']}"
                    elif elem.get("text"):
                        # Use text-based selector
                        selector = f"text='{elem['text']}'"
                
                if selector:
                    await page.click(selector)
                    logger.info(f"    ✓ Clicked via Playwright selector: {selector}")
                    return {"success": True, "method": "playwright_selector"}
                else:
                    # Fallback to coordinate click via Playwright
                    if "_found_element" in step:
                        bbox = step["_found_element"].get("bbox", [0, 0, 0, 0])
                        x = bbox[0] + bbox[2] / 2
                        y = bbox[1] + bbox[3] / 2
                        await page.mouse.click(x, y)
                        return {"success": True, "method": "playwright_mouse"}
            except Exception as e:
                logger.warning(f"  ⚠ Playwright click failed, falling back to PyAutoGUI: {e}")

        if not AUTOMATION_AVAILABLE:
            return {"success": False, "error": "PyAutoGUI not available and Playwright failed"}
        
        # Get target coordinates
        target_coords = None
        
        # Check if element was found in previous step
        if "_found_element" in step:
            elem = step["_found_element"]
            bbox = elem.get("bbox", [0, 0, 0, 0])
            # Click center of element
            target_coords = (
                bbox[0] + bbox[2] // 2,
                bbox[1] + bbox[3] // 2
            )
        elif "target" in step and step["target"] in ["submit_button", "download_link"]:
            # Use coordinates from previous find_element
            return {"success": False, "error": "Target not found"}
        else:
            # Direct coordinates
            target_coords = (step.get("x"), step.get("y"))
        
        if not target_coords or None in target_coords:
            return {"success": False, "error": "No valid coordinates for click"}
        
        try:
            # Human-like movement
            await self._move_mouse_human(target_coords[0], target_coords[1])
            
            # Small random delay before click
            await asyncio.sleep(random.uniform(0.05, 0.15))
            
            # Click
            pyautogui.click()
            
            logger.info(f"    ✓ Clicked at ({target_coords[0]}, {target_coords[1]})")
            
            # Wait for potential page response
            await asyncio.sleep(0.5)
            
            return {
                "success": True,
                "coordinates": target_coords,
                "method": "pyautogui"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_type(
        self,
        step: Dict,
        page_state: Dict,
        page: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Type text with Playwright or PyAutoGUI"""
        text = step.get("value", step.get("text", ""))
        if not text:
            return {"success": False, "error": "No text to type"}

        if page:
            try:
                # If we just clicked an input, it might be focused
                await page.keyboard.type(text, delay=random.randint(50, 150))
                logger.info(f"    ✓ Typed via Playwright keyboard")
                return {"success": True, "method": "playwright_keyboard"}
            except Exception as e:
                logger.warning(f"  ⚠ Playwright type failed, falling back to PyAutoGUI: {e}")

        if not AUTOMATION_AVAILABLE:
            return {"success": False, "error": "PyAutoGUI not available and Playwright failed"}
        
        text = step.get("value", step.get("text", ""))
        if not text:
            return {"success": False, "error": "No text to type"}
        
        try:
            # Type each character with variable delay
            for char in text:
                if self.stopped:
                    break
                
                pyautogui.write(char, interval=0)
                
                # Human-like delay with variance
                delay = self.typing_speed_base + random.uniform(
                    -self.typing_speed_variance,
                    self.typing_speed_variance
                )
                await asyncio.sleep(delay)
            
            logger.info(f"    ✓ Typed text: {text[:50]}{'...' if len(text) > 50 else ''}")
            
            return {
                "success": True,
                "text_length": len(text),
                "method": "pyautogui"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_key_press(self, step: Dict, page: Optional[Any] = None) -> Dict[str, Any]:
        """Press a key (enter, tab, esc, etc.)"""
        key = step.get("key", "enter")
        
        if page:
            try:
                # Playwright expects capitalized keys for some common ones
                pw_key = key
                if key.lower() == "enter": pw_key = "Enter"
                elif key.lower() == "tab": pw_key = "Tab"
                elif key.lower() == "escape": pw_key = "Escape"
                
                await page.keyboard.press(pw_key)
                return {"success": True, "method": "playwright_keyboard"}
            except Exception as e:
                logger.warning(f"  ⚠ Playwright key press failed: {e}")

        if not AUTOMATION_AVAILABLE:
            return {"success": False, "error": "PyAutoGUI not available"}
        
        key = step.get("key", "enter")
        
        try:
            pyautogui.press(key)
            logger.info(f"    ✓ Pressed key: {key}")
            
            await asyncio.sleep(0.3)
            
            return {
                "success": True,
                "key": key,
                "method": "pyautogui"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_scroll(self, step: Dict) -> Dict[str, Any]:
        """Scroll with inertia simulation"""
        if not AUTOMATION_AVAILABLE:
            return {"success": False, "error": "PyAutoGUI not available"}
        
        amount = step.get("amount", -300)  # Negative = down
        
        try:
            # Simulate smooth scroll with multiple smaller scrolls
            steps = 5
            step_amount = amount // steps
            
            for _ in range(steps):
                if self.stopped:
                    break
                pyautogui.scroll(step_amount)
                await asyncio.sleep(0.05)
            
            logger.info(f"    ✓ Scrolled {amount} pixels")
            
            return {
                "success": True,
                "amount": amount,
                "method": "pyautogui"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_navigate(self, step: Dict, page: Optional[Any] = None) -> Dict[str, Any]:
        """Navigate to URL"""
        url = step.get("target")
        
        if not url:
            return {"success": False, "error": "No target URL specified"}
            
        # Ensure URL has protocol
        if not url.startswith(("http://", "https://")):
            logger.info(f"    → Prepended https:// to {url}")
            url = f"https://{url}"
            
        if page:
            try:
                await page.goto(url, wait_until="networkidle")
                return {"success": True, "url": url, "method": "playwright"}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        # This would integrate with active browser
        # For now, log the intent
        logger.info(f"    → Navigate to: {url}")
        
        return {
            "success": True,
            "url": url,
            "method": "placeholder"
        }
    
    async def _execute_screenshot(self, step: Dict, page: Optional[Any] = None) -> Dict[str, Any]:
        """Take a screenshot of the current page or screen"""
        path = step.get("path", "screenshot.png")
        full_page = step.get("full_page", False)
        
        logger.info(f"    → Taking screenshot: {path}")
        
        if page:
            try:
                await page.screenshot(path=path, full_page=full_page)
                return {"success": True, "path": path, "method": "playwright"}
            except Exception as e:
                logger.error(f"Playwright screenshot failed: {e}")
        
        # Fallback to PyAutoGUI for full screen
        if AUTOMATION_AVAILABLE:
            try:
                pyautogui.screenshot(path)
                return {"success": True, "path": path, "method": "pyautogui"}
            except Exception as e:
                return {"success": False, "error": str(e)}
                
        return {"success": False, "error": "No screenshot method available"}
    
    async def _execute_wait(self, step: Dict) -> Dict[str, Any]:
        """Wait for specified duration or condition"""
        duration = step.get("duration", step.get("timeout", 1.0))
        
        await asyncio.sleep(duration)
        
        logger.info(f"    ✓ Waited {duration}s")
        
        return {
            "success": True,
            "duration": duration
        }
    
    async def _execute_verify(
        self,
        step: Dict,
        page_state: Dict
    ) -> Dict[str, Any]:
        """Verify task completion"""
        verification = step.get("verification", {})
        goal = verification.get("goal", "unknown")
        
        # Simple verification based on page state
        context = page_state.get("page_context", {})
        
        # Check for success indicators
        ocr_text = page_state.get("ocr_text", "").lower()
        success_indicators = ["success", "complete", "done", "thank you", "confirmed"]
        
        if any(indicator in ocr_text for indicator in success_indicators):
            logger.info(f"    ✓ Verification passed: success indicator found")
            return {"success": True, "verified": True}
        
        # Check for error indicators
        if context.get("has_errors"):
            logger.warning(f"    ⚠ Verification uncertain: errors detected")
            return {"success": True, "verified": False, "has_errors": True}
        
        logger.info(f"    ? Verification unclear")
        return {"success": True, "verified": "unknown"}
    
    async def _move_mouse_human(self, target_x: int, target_y: int):
        """
        Move mouse with human-like Bezier curve path.
        """
        if not AUTOMATION_AVAILABLE:
            return
        
        current_x, current_y = pyautogui.position()
        
        # Generate Bezier curve points
        points = self._generate_bezier_curve(
            current_x, current_y,
            target_x, target_y,
            num_points=self.mouse_curve_points
        )
        
        # Move along curve with variable speed
        for i, (x, y) in enumerate(points):
            if self.stopped:
                break
            
            pyautogui.moveTo(int(x), int(y), duration=0)
            
            # Slight delay between points
            await asyncio.sleep(self.mouse_speed_base / self.mouse_curve_points)
    
    def _generate_bezier_curve(
        self,
        start_x: int, start_y: int,
        end_x: int, end_y: int,
        num_points: int = 10
    ) -> list:
        """
        Generate quadratic Bezier curve points for natural mouse movement.
        """
        # Control point with randomness for natural curve
        control_x = (start_x + end_x) / 2 + random.randint(-50, 50)
        control_y = (start_y + end_y) / 2 + random.randint(-50, 50)
        
        points = []
        for i in range(num_points + 1):
            t = i / num_points
            
            # Quadratic Bezier formula
            x = (1 - t)**2 * start_x + 2 * (1 - t) * t * control_x + t**2 * end_x
            y = (1 - t)**2 * start_y + 2 * (1 - t) * t * control_y + t**2 * end_y
            
            points.append((x, y))
        
        return points
