"""
Multi-Layer Perception Engine
==============================

Combines visual, semantic, and structural analysis of web pages.
- Screenshot analysis with OCR
- DOM/Accessibility tree traversal
- Visual bounding box detection
- Semantic element understanding
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
import base64
from io import BytesIO

try:
    from PIL import Image, ImageGrab
    import pytesseract
    import cv2
    import numpy as np
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    from playwright.async_api import async_playwright, Page
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    BROWSER_AVAILABLE = True
except ImportError:
    BROWSER_AVAILABLE = False

logger = logging.getLogger(__name__)


class PerceptionEngine:
    """
    Multi-modal perception of web pages using visual + semantic analysis.
    """
    
    def __init__(self):
        self.ocr_cache = {}
        self.element_cache = {}
        logger.info(f"✓ Perception Engine initialized (OCR: {OCR_AVAILABLE}, Browser: {BROWSER_AVAILABLE})")
    
    async def analyze_page(
        self,
        include_screenshot: bool = True,
        include_dom: bool = True,
        include_ocr: bool = True,
        target_url: Optional[str] = None,
        page: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive page analysis combining multiple perception layers.
        
        Returns:
            Dictionary containing:
            - screenshot: Base64 encoded image
            - dom_elements: Semantic element tree
            - ocr_text: Extracted text with coordinates
            - clickable_elements: Interactive elements with bounding boxes
            - page_metadata: URL, title, viewport size
        """
        logger.info("🔍 Analyzing page state...")
        
        result = {
            "timestamp": asyncio.get_event_loop().time(),
            "layers": []
        }
        
        # Layer 1: Visual perception
        if include_screenshot:
            visual_data = await self._capture_visual_layer(page=page)
            result["screenshot"] = visual_data.get("image_b64")
            result["viewport"] = visual_data.get("viewport")
            result["layers"].append("visual")
            
            # Extract OCR text from screenshot
            if include_ocr and OCR_AVAILABLE:
                ocr_data = await self._extract_ocr(visual_data.get("image"))
                result["ocr_text"] = ocr_data.get("text")
                result["ocr_boxes"] = ocr_data.get("boxes")
                result["layers"].append("ocr")
        
        # Layer 2: DOM/Accessibility tree
        if include_dom and (BROWSER_AVAILABLE or page):
            dom_data = await self._analyze_dom(page=page)
            result["dom_elements"] = dom_data.get("elements")
            result["clickable_elements"] = dom_data.get("clickable")
            result["form_fields"] = dom_data.get("forms")
            result["layers"].append("dom")
        
        # Layer 3: Semantic understanding
        semantic_data = await self._semantic_analysis(result)
        result["semantic_elements"] = semantic_data.get("categorized")
        result["page_context"] = semantic_data.get("context")
        result["layers"].append("semantic")
        
        logger.info(f"✓ Page analysis complete ({len(result['layers'])} layers)")
        return result
    
    async def _capture_visual_layer(self, page: Optional[Any] = None) -> Dict[str, Any]:
        """Capture screenshot and visual properties"""
        try:
            if page:
                # Use Playwright screenshot
                screenshot_bytes = await page.screenshot()
                screenshot = Image.open(BytesIO(screenshot_bytes))
            else:
                # Try to grab active window/screen
                screenshot = ImageGrab.grab()
                buffered = BytesIO()
                screenshot.save(buffered, format="PNG")
                screenshot_bytes = buffered.getvalue()
            
            # Convert to base64
            img_b64 = base64.b64encode(screenshot_bytes).decode()
            
            return {
                "image": screenshot,
                "image_b64": img_b64,
                "viewport": {
                    "width": screenshot.width,
                    "height": screenshot.height
                }
            }
        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
            return {}
    
    async def _extract_ocr(self, image: Optional[Image.Image]) -> Dict[str, Any]:
        """Extract text and bounding boxes using OCR"""
        if not image or not OCR_AVAILABLE:
            return {"text": "", "boxes": []}
        
        try:
            # Convert to opencv format
            img_array = np.array(image)
            img_gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            # Run OCR with detailed data
            ocr_data = pytesseract.image_to_data(
                img_gray,
                output_type=pytesseract.Output.DICT
            )
            
            # Extract text and bounding boxes
            boxes = []
            full_text = []
            
            for i in range(len(ocr_data['text'])):
                text = ocr_data['text'][i].strip()
                if text:
                    boxes.append({
                        "text": text,
                        "x": ocr_data['left'][i],
                        "y": ocr_data['top'][i],
                        "width": ocr_data['width'][i],
                        "height": ocr_data['height'][i],
                        "confidence": ocr_data['conf'][i]
                    })
                    full_text.append(text)
            
            return {
                "text": " ".join(full_text),
                "boxes": boxes,
                "total_words": len(boxes)
            }
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return {"text": "", "boxes": []}
    
    async def _analyze_dom(self, page: Optional[Any] = None) -> Dict[str, Any]:
        """Analyze DOM structure and accessibility tree using Playwright if available"""
        if not page:
            return {
                "elements": [],
                "clickable": [],
                "forms": []
            }
            
        try:
            # Execute script to find interactive elements
            elements = await page.evaluate("""() => {
                const results = [];
                const interactives = document.querySelectorAll('button, input, select, textarea, a, [role="button"]');
                
                interactives.forEach(el => {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        results.push({
                            tag: el.tagName.toLowerCase(),
                            text: el.innerText || el.placeholder || el.value || el.ariaLabel || "",
                            type: el.type || "",
                            role: el.getAttribute('role') || "",
                            bbox: [rect.x, rect.y, rect.width, rect.height],
                            id: el.id,
                            className: el.className
                        });
                    }
                });
                return results;
            }""")
            
            clickable = [e for e in elements if e['tag'] in ['button', 'a'] or e['role'] == 'button']
            forms = [e for e in elements if e['tag'] in ['input', 'select', 'textarea']]
            
            return {
                "elements": elements,
                "clickable": clickable,
                "forms": forms
            }
        except Exception as e:
            logger.error(f"DOM analysis failed: {e}")
            return {"elements": [], "clickable": [], "forms": []}
    
    async def _semantic_analysis(self, perception_data: Dict) -> Dict[str, Any]:
        """
        Categorize elements by semantic meaning.
        
        Combines visual + DOM data to understand:
        - Buttons (submit, cancel, navigation)
        - Input fields (email, password, search)
        - Links (navigation, downloads)
        - Content areas
        """
        categorized = {
            "buttons": [],
            "inputs": [],
            "links": [],
            "content": []
        }
        
        # Analyze OCR text for button-like patterns
        if "ocr_boxes" in perception_data:
            for box in perception_data["ocr_boxes"]:
                text_lower = box["text"].lower()
                
                # Button patterns
                if any(word in text_lower for word in [
                    'submit', 'login', 'sign in', 'sign up', 'search',
                    'continue', 'next', 'confirm', 'ok', 'cancel', 'close'
                ]):
                    categorized["buttons"].append({
                        "text": box["text"],
                        "type": "button",
                        "bbox": [box["x"], box["y"], box["width"], box["height"]],
                        "confidence": "visual"
                    })
                
                # Link patterns
                elif any(word in text_lower for word in [
                    'download', 'learn more', 'read more', 'view', 'see'
                ]):
                    categorized["links"].append({
                        "text": box["text"],
                        "type": "link",
                        "bbox": [box["x"], box["y"], box["width"], box["height"]],
                        "confidence": "visual"
                    })
                
                # Input field labels
                elif any(word in text_lower for word in [
                    'email', 'username', 'password', 'search', 'name',
                    'address', 'phone', 'message'
                ]):
                    categorized["inputs"].append({
                        "text": box["text"],
                        "type": "input_label",
                        "bbox": [box["x"], box["y"], box["width"], box["height"]],
                        "confidence": "visual"
                    })
        
        # Page context from OCR text
        full_text = perception_data.get("ocr_text", "").lower()
        context = {
            "has_login": any(word in full_text for word in ['login', 'sign in', 'log in']),
            "has_search": 'search' in full_text,
            "has_forms": any(word in full_text for word in ['submit', 'form', 'required']),
            "has_errors": any(word in full_text for word in ['error', 'invalid', 'required', 'failed']),
            "page_type": self._classify_page_type(full_text)
        }
        
        return {
            "categorized": categorized,
            "context": context
        }
    
    def _classify_page_type(self, text: str) -> str:
        """Classify the type of page based on content"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['login', 'sign in', 'password']):
            return "authentication"
        elif any(word in text_lower for word in ['cart', 'checkout', 'purchase', 'payment']):
            return "commerce"
        elif any(word in text_lower for word in ['search results', 'found', 'matches']):
            return "search_results"
        elif any(word in text_lower for word in ['dashboard', 'welcome back', 'overview']):
            return "dashboard"
        elif any(word in text_lower for word in ['settings', 'preferences', 'profile']):
            return "settings"
        else:
            return "content"
    
    async def find_element(
        self,
        target_description: str,
        element_type: Optional[str] = None,
        visual_hints: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Multi-modal element finding using visual + semantic cues.
        
        Args:
            target_description: What to look for ("submit button", "email field")
            element_type: Type hint ("button", "input", "link")
            visual_hints: Text patterns to look for
            
        Returns:
            Element info with coordinates and interaction method
        """
        logger.info(f"🔍 Finding element: {target_description}")
        
        # Get current page state
        page_state = await self.analyze_page()
        
        # Search in semantic categorized elements
        if element_type in page_state.get("semantic_elements", {}):
            candidates = page_state["semantic_elements"][element_type]
            
            for candidate in candidates:
                if visual_hints:
                    if any(hint.lower() in candidate["text"].lower() for hint in visual_hints):
                        logger.info(f"✓ Found via visual hint: {candidate['text']}")
                        return candidate
        
        # Search in OCR boxes
        if visual_hints and "ocr_boxes" in page_state:
            for box in page_state["ocr_boxes"]:
                if any(hint.lower() in box["text"].lower() for hint in visual_hints):
                    logger.info(f"✓ Found via OCR: {box['text']}")
                    return {
                        "text": box["text"],
                        "bbox": [box["x"], box["y"], box["width"], box["height"]],
                        "method": "visual_click"
                    }
        
        logger.warning(f"⚠ Element not found: {target_description}")
        return None
    
    async def verify_page_state(
        self,
        expected_conditions: Dict[str, Any]
    ) -> bool:
        """
        Verify page meets expected conditions.
        
        Args:
            expected_conditions: Dict with conditions like:
                - url_contains: "dashboard"
                - text_visible: "Welcome back"
                - element_exists: "logout button"
        
        Returns:
            True if all conditions met
        """
        page_state = await self.analyze_page()
        
        for condition_type, condition_value in expected_conditions.items():
            if condition_type == "text_visible":
                ocr_text = page_state.get("ocr_text", "").lower()
                if condition_value.lower() not in ocr_text:
                    logger.warning(f"✗ Expected text not found: {condition_value}")
                    return False
            
            elif condition_type == "element_exists":
                element = await self.find_element(condition_value)
                if not element:
                    logger.warning(f"✗ Expected element not found: {condition_value}")
                    return False
        
        logger.info("✓ Page state verified")
        return True
