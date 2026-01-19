import json
import os
import time
from datetime import datetime
from collections import defaultdict
import threading
import numpy as np
from PIL import Image, ImageGrab

try:
    from pynput import mouse, keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False

try:
    import pytesseract
    import cv2
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("⚠️  OCR not available. Install: pip install pytesseract opencv-python")

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

class BehavioralMacroEngine:
    def __init__(self, data_dir="data/macros"):
        self.data_dir = data_dir
        self.history_file = os.path.join(data_dir, "action_history.json")
        self.macros_dir = os.path.join(data_dir, "registry")
        self.screenshots_dir = os.path.join(data_dir, "screenshots")
        
        # Ensure directories exist
        os.makedirs(self.macros_dir, exist_ok=True)
        os.makedirs(self.screenshots_dir, exist_ok=True)
        
        # In-memory state
        self.action_history = self._load_history()
        self.macros = self._load_macros()
        self.active_session = []
        self.lock = threading.Lock()
        
        # Recording state
        self.is_recording = False
        self.recorded_actions = []
        self.last_action_time = None
        self.mouse_listener = None
        self.keyboard_listener = None
        
        # OCR and pattern recognition
        self.ocr_cache = {}  # Cache OCR results for performance
        self.visual_anchors = {}  # Store visual reference points
        
    def capture_screen_context(self, x, y, width=200, height=100):
        """Capture a region around coordinates for OCR and visual matching"""
        if not OCR_AVAILABLE:
            return None
            
        try:
            # Capture region around the point
            screenshot = ImageGrab.grab(bbox=(
                max(0, x - width // 2),
                max(0, y - height // 2),
                x + width // 2,
                y + height // 2
            ))
            
            # Convert to opencv format
            img_array = np.array(screenshot)
            img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            
            # OCR on the region
            text = pytesseract.image_to_string(screenshot)
            
            return {
                "text": text.strip(),
                "image_hash": hash(screenshot.tobytes()),
                "region": (x, y, width, height)
            }
        except Exception as e:
            print(f"Screen capture error: {e}")
            return None

    def start_recording(self):
        with self.lock:
            self.is_recording = True
            self.recorded_actions = []
            self.last_action_time = time.time()
        
        if PYNPUT_AVAILABLE:
            self.start_input_listeners()
            print("✓ Macro recording started with smart timing and OCR")
            
    def stop_recording(self, name: str, description: str = ""):
        if PYNPUT_AVAILABLE:
            self.stop_input_listeners()

        with self.lock:
            self.is_recording = False
            if not self.recorded_actions:
                return None
            
            # Create macro from recorded actions
            macro_id = f"macro_{int(time.time())}"
            macro = {
                "id": macro_id,
                "name": name,
                "description": description,
                "steps": self.recorded_actions, # Store full steps
                "created_at": datetime.now().isoformat()
            }
            
            with open(os.path.join(self.macros_dir, f"{macro_id}.json"), 'w') as f:
                json.dump(macro, f, indent=2)
                
            self.macros[macro_id] = macro
            return macro

    def start_input_listeners(self):
        self.mouse_listener = mouse.Listener(on_click=self.on_click)
        self.keyboard_listener = keyboard.Listener(on_release=self.on_release)
        self.mouse_listener.start()
        self.keyboard_listener.start()

    def stop_input_listeners(self):
        if self.mouse_listener:
            self.mouse_listener.stop()
            self.mouse_listener = None
        if self.keyboard_listener:
            self.keyboard_listener.stop()
            self.keyboard_listener = None

    def on_click(self, x, y, button, pressed):
        if pressed and self.is_recording:
            try:
                current_time = time.time()
                delay = current_time - self.last_action_time if self.last_action_time else 0
                
                btn = str(button).replace('Button.', '')
                
                # Capture screen context around click for OCR
                screen_context = self.capture_screen_context(x, y) if OCR_AVAILABLE else None
                
                action = {
                    "timestamp": datetime.now().isoformat(),
                    "agent": "user",
                    "tool": "click",
                    "action": "execute",
                    "params": {"x": x, "y": y, "button": btn},
                    "delay": round(delay, 3),  # Precise delay in seconds
                    "screen_context": screen_context  # OCR text and visual info
                }
                with self.lock:
                    self.recorded_actions.append(action)
                    self.last_action_time = current_time
                    
                print(f"✓ Recorded click at ({x}, {y}) with {delay:.2f}s delay")
            except Exception as e:
                print(f"Error recording click: {e}")

    def on_release(self, key):
        if self.is_recording:
            try:
                current_time = time.time()
                delay = current_time - self.last_action_time if self.last_action_time else 0
                
                # Check for stop key (e.g. Esc) if needed, but we use UI button
                try:
                    k = key.char
                    if k:
                        action = {
                            "timestamp": datetime.now().isoformat(),
                            "agent": "user",
                            "tool": "type_text",
                            "action": "execute",
                            "params": {"text": k},
                            "delay": round(delay, 3)
                        }
                        with self.lock:
                            self.recorded_actions.append(action)
                            self.last_action_time = current_time
                except AttributeError:
                    k = str(key).replace('Key.', '')
                    action = {
                        "timestamp": datetime.now().isoformat(),
                        "agent": "user",
                        "tool": "press_key",
                        "action": "execute",
                        "params": {"key": k},
                        "delay": round(delay, 3)
                    }
                    with self.lock:
                        self.recorded_actions.append(action)
                        self.last_action_time = current_time
            except Exception as e:
                print(f"Error recording key: {e}")

    def _load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []

    def _load_macros(self):
        macros = {}
        if os.path.exists(self.macros_dir):
            for filename in os.listdir(self.macros_dir):
                if filename.endswith(".json"):
                    try:
                        with open(os.path.join(self.macros_dir, filename), 'r') as f:
                            macro = json.load(f)
                            macros[macro['id']] = macro
                    except Exception as e:
                        print(f"Error loading macro {filename}: {e}")
        return macros

    def _save_history(self):
        # Keep only last 1000 actions to prevent bloat
        if len(self.action_history) > 1000:
            self.action_history = self.action_history[-1000:]
        
        with open(self.history_file, 'w') as f:
            json.dump(self.action_history, f, indent=2)

    def log_action(self, tool, action, params=None, agent="user"):
        """
        Log a user or agent action to the history.
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": agent,
            "tool": tool,
            "action": action,
            "params": params or {},
            "session_id": "current" # Could be tied to actual session IDs
        }
        
        with self.lock:
            self.action_history.append(entry)
            self.active_session.append(entry)
            
            if self.is_recording:
                self.recorded_actions.append(entry)
                
            self._save_history()
            
            # Trigger pattern detection on every log (simplified for now)
            # In production, this might be async or periodic
            self.detect_patterns()

    def detect_patterns(self):
        """
        Analyze history for repeated sequences (N-grams).
        Simple implementation: looks for exact sequences of tool+action of length 2-5.
        """
        if len(self.action_history) < 5:
            return []

        # Simplify history to signature strings "tool:action"
        signatures = [f"{e['tool']}:{e['action']}" for e in self.action_history]
        
        patterns = defaultdict(int)
        
        # Look for sequences of length 2 to 5
        for n in range(2, 6):
            for i in range(len(signatures) - n + 1):
                seq = tuple(signatures[i:i+n])
                patterns[seq] += 1
        
        # Filter for patterns that appear at least 3 times
        significant_patterns = []
        for seq, count in patterns.items():
            if count >= 3:
                significant_patterns.append({
                    "sequence": seq,
                    "count": count,
                    "confidence": min(0.5 + (count * 0.1), 0.95) # Cap at 0.95
                })
        
        # Sort by length (desc) then count (desc)
        significant_patterns.sort(key=lambda x: (len(x['sequence']), x['count']), reverse=True)
        
        return significant_patterns

    def create_macro_from_pattern(self, pattern_seq, name, description="Auto-generated macro"):
        """
        Convert a detected pattern sequence into a saved macro.
        """
        # Reconstruct the steps from the last occurrence of this sequence
        # This is a simplification; ideally we'd average parameters or parameterize them
        
        steps = []
        # Find the sequence in history to get sample params
        signatures = [f"{e['tool']}:{e['action']}" for e in self.action_history]
        target_seq = tuple(pattern_seq)
        
        found_idx = -1
        # Search backwards to find most recent
        for i in range(len(signatures) - len(target_seq), -1, -1):
            if tuple(signatures[i:i+len(target_seq)]) == target_seq:
                found_idx = i
                break
        
        if found_idx != -1:
            for i in range(len(target_seq)):
                hist_entry = self.action_history[found_idx + i]
                steps.append({
                    "tool": hist_entry['tool'],
                    "action": hist_entry['action'],
                    "params": hist_entry['params']
                })

        macro_id = f"macro_{int(time.time())}"
        macro = {
            "id": macro_id,
            "name": name,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "steps": steps,
            "trigger": "manual", # Default
            "autonomous": False
        }
        
        # Save to disk
        with open(os.path.join(self.macros_dir, f"{macro_id}.json"), 'w') as f:
            json.dump(macro, f, indent=2)
            
        with self.lock:
            self.macros[macro_id] = macro
            
        return macro

    def get_macros(self):
        return list(self.macros.values())

    def get_macro(self, macro_id):
        return self.macros.get(macro_id)

    def update_macro(self, macro_id, updates):
        if macro_id not in self.macros:
            return None
        
        macro = self.macros[macro_id]
        # Update fields
        for key, value in updates.items():
            if key in ['name', 'description', 'steps', 'settings']:
                macro[key] = value
        
        macro['updated_at'] = datetime.now().isoformat()
        
        # Save to disk
        with open(os.path.join(self.macros_dir, f"{macro_id}.json"), 'w') as f:
            json.dump(macro, f, indent=2)
            
        with self.lock:
            self.macros[macro_id] = macro
            
        return macro

    def delete_macro(self, macro_id):
        if macro_id in self.macros:
            # Remove from disk
            try:
                os.remove(os.path.join(self.macros_dir, f"{macro_id}.json"))
            except OSError:
                pass
            
            # Remove from memory
            with self.lock:
                del self.macros[macro_id]
            return True
        return False

    def get_recent_history(self, limit=50):
        return self.action_history[-limit:]

    def execute_macro(self, macro_id, executor_func, speed=1.0, loops=1):
        """
        Execute a macro by ID with intelligent timing and OCR-based verification.
        executor_func is a callback that takes (tool, action, params) and executes it.
        """
        macro = self.macros.get(macro_id)
        if not macro:
            return {"success": False, "error": "Macro not found"}
            
        results = []
        
        # Default settings from macro if not provided
        macro_settings = macro.get('settings', {})
        speed = float(speed) if speed else macro_settings.get('speed', 1.0)
        loops = int(loops) if loops else macro_settings.get('loops', 1)
        
        print(f"▶ Executing macro '{macro.get('name', macro_id)}' - Speed: {speed}x, Loops: {loops}")
        
        for loop_idx in range(loops):
            for step_idx, step in enumerate(macro['steps']):
                try:
                    # Apply recorded delay between actions (scaled by speed)
                    recorded_delay = step.get('delay', 0.1)
                    actual_delay = recorded_delay / speed if speed > 0 else recorded_delay
                    
                    # Minimum delay to ensure UI responsiveness
                    actual_delay = max(actual_delay, 0.05)
                    
                    time.sleep(actual_delay)
                    
                    # OCR-based intelligent click positioning (if screen context available)
                    if step['tool'] == 'click' and step.get('screen_context') and OCR_AVAILABLE:
                        optimized_coords = self._find_optimal_click_position(step)
                        if optimized_coords:
                            step['params']['x'], step['params']['y'] = optimized_coords
                            print(f"  ✓ OCR-adjusted click position to {optimized_coords}")
                    
                    # Execute step
                    res = executor_func(step['tool'], step['action'], step['params'])
                    results.append({
                        "loop": loop_idx + 1,
                        "step": step_idx + 1,
                        "step_data": step,
                        "result": res,
                        "success": True
                    })
                    
                    print(f"  ✓ Step {step_idx + 1}/{len(macro['steps'])} - {step['tool']} (delay: {actual_delay:.2f}s)")
                    
                except Exception as e:
                    error_msg = str(e)
                    results.append({
                        "loop": loop_idx + 1,
                        "step": step_idx + 1,
                        "step_data": step,
                        "error": error_msg,
                        "success": False
                    })
                    print(f"  ✗ Error on step {step_idx + 1}: {error_msg}")
                    # Continue on error instead of stopping (configurable)
                    continue
                
        print(f"✓ Macro execution complete: {len(results)} steps executed")
        return {"success": True, "results": results, "total_steps": len(results)}
    
    def _find_optimal_click_position(self, step):
        """Use OCR to find the best click position if screen content has moved"""
        try:
            screen_context = step.get('screen_context')
            if not screen_context or not screen_context.get('text'):
                return None
            
            original_x = step['params']['x']
            original_y = step['params']['y']
            search_text = screen_context['text'][:50]  # First 50 chars
            
            if not search_text.strip():
                return None
            
            # Capture current screen in search area
            current_context = self.capture_screen_context(original_x, original_y, width=400, height=200)
            
            if current_context and search_text in current_context.get('text', ''):
                # Text found in expected location - use original coords
                return None
            
            # TODO: Implement visual search across wider area if text not found
            # For now, return None to use original coordinates
            return None
            
        except Exception as e:
            print(f"  OCR positioning error: {e}")
            return None

# Singleton instance
_engine = None

def get_macro_engine():
    global _engine
    if _engine is None:
        # Adjust path relative to where this is run
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_path = os.path.join(base_path, "data", "macros")
        _engine = BehavioralMacroEngine(data_dir=data_path)
    return _engine
