"""
Computer Control Module - Keyboard, Mouse, Screen automation
Uses pyautogui for cross-platform computer control
"""
import time
import base64
import io
from typing import Tuple, Optional, List

try:
    import pyautogui
    pyautogui.FAILSAFE = True  # Move mouse to corner to abort
    pyautogui.PAUSE = 0.1  # Small pause between actions
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class ComputerController:
    """Controls keyboard, mouse, and screen capture"""
    
    def __init__(self):
        self.available = PYAUTOGUI_AVAILABLE
        if not self.available:
            print("WARNING: pyautogui not installed. Run: pip install pyautogui")
    
    # --- Keyboard Actions ---
    
    def type_text(self, text: str, interval: float = 0.02) -> dict:
        """Type text character by character (like a human)"""
        if not self.available:
            return {"success": False, "error": "pyautogui not installed"}
        
        try:
            pyautogui.typewrite(text, interval=interval)
            return {"success": True, "typed": text}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def type_unicode(self, text: str) -> dict:
        """Type text including unicode characters (slower but supports all chars)"""
        if not self.available:
            return {"success": False, "error": "pyautogui not installed"}
        
        try:
            # pyautogui.write() uses clipboard for unicode
            pyautogui.write(text)
            return {"success": True, "typed": text}
        except Exception as e:
            # Fallback: use keyboard library or hotkey paste
            try:
                import pyperclip
                pyperclip.copy(text)
                pyautogui.hotkey('ctrl', 'v')
                return {"success": True, "typed": text, "method": "clipboard"}
            except:
                return {"success": False, "error": str(e)}
    
    def press_key(self, key: str) -> dict:
        """Press a single key (enter, tab, escape, f1, etc.)"""
        if not self.available:
            return {"success": False, "error": "pyautogui not installed"}
        
        try:
            pyautogui.press(key)
            return {"success": True, "pressed": key}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def hotkey(self, *keys) -> dict:
        """Press a keyboard shortcut (e.g., ctrl+c, ctrl+shift+s)"""
        if not self.available:
            return {"success": False, "error": "pyautogui not installed"}
        
        try:
            pyautogui.hotkey(*keys)
            return {"success": True, "hotkey": "+".join(keys)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def key_down(self, key: str) -> dict:
        """Hold down a key"""
        if not self.available:
            return {"success": False, "error": "pyautogui not installed"}
        
        try:
            pyautogui.keyDown(key)
            return {"success": True, "held": key}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def key_up(self, key: str) -> dict:
        """Release a key"""
        if not self.available:
            return {"success": False, "error": "pyautogui not installed"}
        
        try:
            pyautogui.keyUp(key)
            return {"success": True, "released": key}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # --- Mouse Actions ---
    
    def move_mouse(self, x: int, y: int, duration: float = 0.25) -> dict:
        """Move mouse to absolute position"""
        if not self.available:
            return {"success": False, "error": "pyautogui not installed"}
        
        try:
            pyautogui.moveTo(x, y, duration=duration)
            return {"success": True, "position": (x, y)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def move_mouse_relative(self, dx: int, dy: int, duration: float = 0.25) -> dict:
        """Move mouse relative to current position"""
        if not self.available:
            return {"success": False, "error": "pyautogui not installed"}
        
        try:
            pyautogui.move(dx, dy, duration=duration)
            pos = pyautogui.position()
            return {"success": True, "new_position": (pos.x, pos.y)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def click(self, x: Optional[int] = None, y: Optional[int] = None, 
              button: str = "left", clicks: int = 1) -> dict:
        """Click at position (or current position if x,y not specified)"""
        if not self.available:
            return {"success": False, "error": "pyautogui not installed"}
        
        try:
            if x is not None and y is not None:
                pyautogui.click(x, y, clicks=clicks, button=button)
                pos = (x, y)
            else:
                pyautogui.click(clicks=clicks, button=button)
                pos = pyautogui.position()
                pos = (pos.x, pos.y)
            return {"success": True, "clicked_at": pos, "button": button, "clicks": clicks}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def double_click(self, x: Optional[int] = None, y: Optional[int] = None) -> dict:
        """Double-click at position"""
        return self.click(x, y, clicks=2)
    
    def right_click(self, x: Optional[int] = None, y: Optional[int] = None) -> dict:
        """Right-click at position"""
        return self.click(x, y, button="right")
    
    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int, 
             duration: float = 0.5, button: str = "left") -> dict:
        """Drag from one position to another"""
        if not self.available:
            return {"success": False, "error": "pyautogui not installed"}
        
        try:
            pyautogui.moveTo(start_x, start_y)
            pyautogui.drag(end_x - start_x, end_y - start_y, duration=duration, button=button)
            return {"success": True, "dragged": {"from": (start_x, start_y), "to": (end_x, end_y)}}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def scroll(self, amount: int, x: Optional[int] = None, y: Optional[int] = None) -> dict:
        """Scroll up (positive) or down (negative)"""
        if not self.available:
            return {"success": False, "error": "pyautogui not installed"}
        
        try:
            if x is not None and y is not None:
                pyautogui.scroll(amount, x, y)
            else:
                pyautogui.scroll(amount)
            return {"success": True, "scrolled": amount}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_mouse_position(self) -> dict:
        """Get current mouse position"""
        if not self.available:
            return {"success": False, "error": "pyautogui not installed"}
        
        try:
            pos = pyautogui.position()
            return {"success": True, "x": pos.x, "y": pos.y}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # --- Screen Actions ---
    
    def screenshot(self, region: Optional[Tuple[int, int, int, int]] = None, 
                   save_path: Optional[str] = None) -> dict:
        """Take a screenshot (full screen or region)"""
        if not self.available:
            return {"success": False, "error": "pyautogui not installed"}
        
        try:
            if region:
                img = pyautogui.screenshot(region=region)
            else:
                img = pyautogui.screenshot()
            
            if save_path:
                img.save(save_path)
                return {"success": True, "saved_to": save_path, "size": img.size}
            else:
                # Return base64 encoded image
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                return {"success": True, "image_base64": b64[:100] + "...", "size": img.size, "full_base64": b64}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_screen_size(self) -> dict:
        """Get screen dimensions"""
        if not self.available:
            return {"success": False, "error": "pyautogui not installed"}
        
        try:
            size = pyautogui.size()
            return {"success": True, "width": size.width, "height": size.height}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def locate_on_screen(self, image_path: str, confidence: float = 0.9) -> dict:
        """Find an image on screen and return its position"""
        if not self.available:
            return {"success": False, "error": "pyautogui not installed"}
        
        try:
            location = pyautogui.locateOnScreen(image_path, confidence=confidence)
            if location:
                center = pyautogui.center(location)
                return {"success": True, "found": True, "location": {
                    "left": location.left, "top": location.top,
                    "width": location.width, "height": location.height,
                    "center": (center.x, center.y)
                }}
            else:
                return {"success": True, "found": False}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def click_image(self, image_path: str, confidence: float = 0.9) -> dict:
        """Find an image on screen and click it"""
        if not self.available:
            return {"success": False, "error": "pyautogui not installed"}
        
        try:
            location = pyautogui.locateCenterOnScreen(image_path, confidence=confidence)
            if location:
                pyautogui.click(location)
                return {"success": True, "clicked_at": (location.x, location.y)}
            else:
                return {"success": False, "error": "Image not found on screen"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # --- Utility ---
    
    def wait(self, seconds: float) -> dict:
        """Wait for specified seconds"""
        time.sleep(seconds)
        return {"success": True, "waited": seconds}
    
    def alert(self, message: str, title: str = "Agent Amigos") -> dict:
        """Show an alert dialog"""
        if not self.available:
            return {"success": False, "error": "pyautogui not installed"}
        
        try:
            pyautogui.alert(message, title)
            return {"success": True, "alerted": message}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def confirm(self, message: str, title: str = "Agent Amigos") -> dict:
        """Show a confirm dialog (OK/Cancel)"""
        if not self.available:
            return {"success": False, "error": "pyautogui not installed"}
        
        try:
            result = pyautogui.confirm(message, title)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def prompt(self, message: str, title: str = "Agent Amigos", default: str = "") -> dict:
        """Show a prompt dialog for text input"""
        if not self.available:
            return {"success": False, "error": "pyautogui not installed"}
        
        try:
            result = pyautogui.prompt(message, title, default)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Singleton instance
computer = ComputerController()
