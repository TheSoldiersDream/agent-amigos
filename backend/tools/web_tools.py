"""
Web Tools Module - Browser automation, web search, page interaction
"""
import os
import time
import json
import platform
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Load social media platforms database
SOCIAL_MEDIA_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "social_media", "platforms.json")
SOCIAL_MEDIA_PLATFORMS = {}
try:
    if os.path.exists(SOCIAL_MEDIA_DB_PATH):
        with open(SOCIAL_MEDIA_DB_PATH, 'r', encoding='utf-8') as f:
            SOCIAL_MEDIA_PLATFORMS = json.load(f)
except Exception:
    logger.debug("Failed to load social media platforms database", exc_info=True)

# Try to import web automation libraries
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.edge.options import Options as EdgeOptions
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.action_chains import ActionChains
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

try:
    from webdriver_manager.microsoft import EdgeChromiumDriverManager
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.edge.service import Service as EdgeService
    from selenium.webdriver.chrome.service import Service as ChromeService
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False

try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False

try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# Import agent coordinator for progress reporting
try:
    from tools.agent_coordinator import agent_working
except ImportError:
    try:
        from .agent_coordinator import agent_working
    except ImportError:
        def agent_working(*args, **kwargs): pass


class WebTools:
    """Web automation and search capabilities"""
    
    def __init__(self):
        self.driver = None
        self.browser_type = None
        self._keep_browser_open = True  # Keep browser open between tool calls
        self._debug_port = 9222  # Chrome debugging port
    
    # --- Browser Control ---
    
    def _is_chrome_debug_running(self) -> bool:
        """Check if Chrome is running with debugging port open"""
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', self._debug_port))
            return result == 0
        except:
            return False
        finally:
            sock.close()
    
    def _start_chrome_with_debugging(self) -> bool:
        """Start Chrome with remote debugging enabled using your profile"""
        import subprocess
        import os
        
        # Find Chrome executable
        chrome_paths = [
            os.path.join(os.environ.get('PROGRAMFILES', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
            os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
        ]
        
        chrome_exe = None
        for path in chrome_paths:
            if os.path.exists(path):
                chrome_exe = path
                break
        
        if not chrome_exe:
            print("[BROWSER] ✗ Chrome not found!")
            return False
        
        # Use your existing Chrome profile
        user_data = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'Chrome', 'User Data')
        
        print(f"[BROWSER] Starting Chrome with debugging on port {self._debug_port}...")
        print(f"[BROWSER] Using your profile: {user_data}")
        
        # Start Chrome with debugging
        cmd = [
            chrome_exe,
            f'--remote-debugging-port={self._debug_port}',
            f'--user-data-dir={user_data}',
            '--profile-directory=Default',
            '--start-maximized'
        ]
        
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(3)  # Wait for Chrome to start
            return self._is_chrome_debug_running()
        except Exception as e:
            print(f"[BROWSER] Failed to start Chrome: {e}")
            return False
    
    def attach_to_existing_browser(self, port: int = None) -> dict:
        """
        Attach to an existing Chrome browser with remote debugging enabled.
        """
        if port is None:
            port = self._debug_port
            
        if not SELENIUM_AVAILABLE:
            return {"success": False, "error": "Selenium not installed"}
        
        try:
            options = ChromeOptions()
            options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
            
            if WEBDRIVER_MANAGER_AVAILABLE:
                service = ChromeService(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=options)
            else:
                self.driver = webdriver.Chrome(options=options)
            
            self.browser_type = "chrome"
            current_url = self.driver.current_url
            title = self.driver.title
            
            print(f"[BROWSER] ✓ Connected to existing Chrome!")
            print(f"[BROWSER] Current URL: {current_url}")
            
            return {
                "success": True, 
                "attached": True,
                "url": current_url,
                "title": title,
                "message": "Connected to existing browser - logins preserved!"
            }
        except Exception as e:
            return {"success": False, "error": f"Could not attach: {str(e)}"}
    
    def open_browser_with_profile(self, profile_name: str = "Default") -> dict:
        """
        Open Chrome using your EXISTING Chrome profile - no new logins needed!
        Uses your actual Chrome profile where you're already logged into Facebook.
        
        IMPORTANT: Close any open Chrome windows first, then run this.
        """
        if not SELENIUM_AVAILABLE:
            return {"success": False, "error": "Selenium not installed"}
        
        # If we already have a valid driver, reuse it
        if self.driver:
            try:
                _ = self.driver.current_url
                print("[BROWSER] ✓ Reusing existing browser window")
                return {"success": True, "reused": True, "url": self.driver.current_url}
            except:
                self.driver = None
        
        try:
            import os
            options = ChromeOptions()
            
            # Use YOUR existing Chrome profile - already logged into Facebook!
            chrome_user_data = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'Chrome', 'User Data')
            
            if os.path.exists(chrome_user_data):
                print(f"[BROWSER] Using your existing Chrome profile: {chrome_user_data}")
                print("[BROWSER] ⚠️  Make sure Chrome is CLOSED before running this!")
                options.add_argument(f"--user-data-dir={chrome_user_data}")
                options.add_argument(f"--profile-directory={profile_name}")
            else:
                print("[BROWSER] Chrome profile not found, using default")
            
            options.add_argument("--start-maximized")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument("--disable-infobars")
            
            if WEBDRIVER_MANAGER_AVAILABLE:
                service = ChromeService(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=options)
            else:
                self.driver = webdriver.Chrome(options=options)
            
            self.browser_type = "chrome"
            
            return {
                "success": True,
                "profile": chrome_user_data,
                "message": "Browser opened with YOUR Chrome profile - already logged in!"
            }
        except Exception as e:
            error_msg = str(e)
            if "user data directory is already in use" in error_msg.lower():
                return {
                    "success": False, 
                    "error": "Chrome is already open! Please CLOSE all Chrome windows first, then try again."
                }
            return {"success": False, "error": error_msg}
    
    def ensure_browser_ready(self, require_facebook: bool = False) -> dict:
        """
        Smart browser detection:
        1. If we have an active driver, reuse it
        2. If Chrome is running with debugging, connect to it
        3. If Chrome is running normally, ask user to close it OR start new debug instance
        4. If no Chrome, start Chrome with debugging and your profile
        """
        import subprocess
        
        # STEP 1: If we already have a valid driver, reuse it
        if self.driver:
            try:
                current_url = self.driver.current_url
                print("[BROWSER] ✓ Reusing existing browser session")
                
                if require_facebook and "facebook.com" not in current_url:
                    print("[BROWSER] Navigating to Facebook...")
                    self.driver.get("https://www.facebook.com")
                    time.sleep(2)
                
                return {"success": True, "method": "existing_session", "url": self.driver.current_url}
            except:
                print("[BROWSER] Previous session invalid, reconnecting...")
                self.driver = None
        
        # STEP 2: Check if Chrome debug port is already open (can connect!)
        if self._is_chrome_debug_running():
            print("[BROWSER] Found Chrome with debugging enabled, connecting...")
            result = self.attach_to_existing_browser()
            if result.get("success"):
                if require_facebook and "facebook.com" not in self.driver.current_url:
                    print("[BROWSER] Navigating to Facebook...")
                    self.driver.get("https://www.facebook.com")
                    time.sleep(2)
                return {"success": True, "method": "attached_to_debug", "url": self.driver.current_url}
        
        # STEP 3: Check if regular Chrome is running (need to restart it)
        try:
            result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq chrome.exe'], 
                                    capture_output=True, text=True, timeout=5)
            chrome_running = 'chrome.exe' in result.stdout.lower()
        except:
            chrome_running = False
        
        if chrome_running:
            print("[BROWSER] ⚠️  Chrome is running but not in debug mode")
            print("[BROWSER] Closing Chrome and restarting with debugging...")
            
            # Kill Chrome processes
            try:
                subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'], 
                              capture_output=True, timeout=10)
                time.sleep(2)
            except:
                pass
        
        # STEP 4: Start Chrome with debugging enabled
        print("[BROWSER] Starting Chrome with your profile and debugging enabled...")
        if self._start_chrome_with_debugging():
            time.sleep(2)
            result = self.attach_to_existing_browser()
            if result.get("success"):
                if require_facebook:
                    print("[BROWSER] Navigating to Facebook...")
                    self.driver.get("https://www.facebook.com")
                    time.sleep(3)
                return {"success": True, "method": "started_debug_chrome", "url": self.driver.current_url}
        
        # STEP 5: Fallback to regular Selenium
        print("[BROWSER] Debug mode failed, trying direct Selenium...")
        open_result = self.open_browser_with_profile()
        
        if open_result.get("success"):
            if require_facebook:
                print("[BROWSER] Navigating to Facebook...")
                self.driver.get("https://www.facebook.com")
                time.sleep(3)
            return {"success": True, "method": "new_browser", "url": self.driver.current_url if self.driver else None}
        
        # Final fallback - basic browser
        print("[BROWSER] Profile failed, trying basic browser...")
        basic_result = self.open_browser()
        if basic_result.get("success"):
            if require_facebook:
                self.driver.get("https://www.facebook.com")
                time.sleep(2)
            return {"success": True, "method": "basic_browser", "url": self.driver.current_url if self.driver else None}
        
        return {
            "success": False, 
            "error": "Could not open browser. Please run 'start_chrome_for_agent.bat' from the AgentAmigos folder first!"
        }

    def open_browser(self, browser: str = "chrome", headless: bool = False, url: Optional[str] = None) -> dict:
        """Open a browser for automation and optionally navigate to a URL"""
        if not SELENIUM_AVAILABLE:
            return {"success": False, "error": "Selenium not installed. Run: pip install selenium"}
        
        try:
            if browser.lower() == "edge":
                options = EdgeOptions()
                if headless:
                    options.add_argument("--headless")
                options.add_argument("--start-maximized")
                if WEBDRIVER_MANAGER_AVAILABLE:
                    service = EdgeService(EdgeChromiumDriverManager().install())
                    self.driver = webdriver.Edge(service=service, options=options)
                else:
                    self.driver = webdriver.Edge(options=options)
                self.browser_type = "edge"
            elif browser.lower() == "chrome":
                options = ChromeOptions()
                if headless:
                    options.add_argument("--headless")
                options.add_argument("--start-maximized")
                if WEBDRIVER_MANAGER_AVAILABLE:
                    service = ChromeService(ChromeDriverManager().install())
                    self.driver = webdriver.Chrome(service=service, options=options)
                else:
                    self.driver = webdriver.Chrome(options=options)
                self.browser_type = "chrome"
            else:
                return {"success": False, "error": f"Unsupported browser: {browser}"}
            
            if url:
                try:
                    self.driver.get(url)
                except Exception as nav_error:
                    return {
                        "success": False,
                        "error": f"Browser opened but navigation failed: {nav_error}",
                        "browser": browser,
                    }
            return {"success": True, "browser": browser, "headless": headless, "url": url}
        except Exception as e:
            extra = ""
            if "Could not reach host" in str(e):
                extra = " (WebDriver download failed. Connect to the internet or install Edge/Chrome WebDriver manually.)"
            return {"success": False, "error": f"{str(e)}{extra}"}
    
    def close_browser(self) -> dict:
        """Close the browser"""
        if not self.driver:
            return {"success": False, "error": "No browser open"}
        
        try:
            self.driver.quit()
            self.driver = None
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def navigate(self, url: str) -> dict:
        """Navigate to a URL"""
        if not self.driver:
            result = self.open_browser()
            if not result["success"]:
                fallback = self.open_url_default_browser(url)
                if fallback.get("success"):
                    fallback.update({
                        "note": "Selenium browser unavailable - opened in default browser instead. Automation controls limited to keyboard/mouse tools.",
                        "url": url
                    })
                    return fallback
                return result
        
        try:
            self.driver.get(url)
            return {"success": True, "url": url, "title": self.driver.title}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_page_content(self) -> dict:
        """Get current page text content"""
        if not self.driver:
            return {"success": False, "error": "No browser open"}
        
        try:
            body = self.driver.find_element(By.TAG_NAME, "body")
            return {
                "success": True,
                "url": self.driver.current_url,
                "title": self.driver.title,
                "text": body.text[:5000]  # Limit to 5000 chars
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_page_html(self) -> dict:
        """Get current page HTML source"""
        if not self.driver:
            return {"success": False, "error": "No browser open"}
        
        try:
            return {
                "success": True,
                "url": self.driver.current_url,
                "title": self.driver.title,
                "html": self.driver.page_source[:10000]  # Limit
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def click_element(self, selector: str, by: str = "css") -> dict:
        """Click an element on the page"""
        if not self.driver:
            return {"success": False, "error": "No browser open"}
        
        by_method = {
            "css": By.CSS_SELECTOR,
            "xpath": By.XPATH,
            "id": By.ID,
            "name": By.NAME,
            "class": By.CLASS_NAME,
            "tag": By.TAG_NAME,
            "link_text": By.LINK_TEXT,
            "partial_link": By.PARTIAL_LINK_TEXT
        }.get(by.lower(), By.CSS_SELECTOR)
        
        try:
            element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((by_method, selector))
            )
            element.click()
            return {"success": True, "clicked": selector}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def type_in_element(self, selector: str, text: str, by: str = "css", 
                        clear_first: bool = True, press_enter: bool = False) -> dict:
        """Type text into an input element"""
        if not self.driver:
            return {"success": False, "error": "No browser open"}
        
        by_method = {
            "css": By.CSS_SELECTOR,
            "xpath": By.XPATH,
            "id": By.ID,
            "name": By.NAME
        }.get(by.lower(), By.CSS_SELECTOR)
        
        try:
            element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((by_method, selector))
            )
            if clear_first:
                element.clear()
            element.send_keys(text)
            if press_enter:
                element.send_keys(Keys.RETURN)
            return {"success": True, "typed": text, "selector": selector}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def take_browser_screenshot(self, save_path: Optional[str] = None) -> dict:
        """Take a screenshot of the browser"""
        if not self.driver:
            return {"success": False, "error": "No browser open"}
        
        try:
            if save_path:
                self.driver.save_screenshot(save_path)
                return {"success": True, "saved_to": save_path}
            else:
                import base64
                screenshot = self.driver.get_screenshot_as_base64()
                return {"success": True, "image_base64": screenshot[:100] + "...", "full_base64": screenshot}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def execute_javascript(self, script: str) -> dict:
        """Execute JavaScript in the browser"""
        if not self.driver:
            return {"success": False, "error": "No browser open"}
        
        try:
            result = self.driver.execute_script(script)
            return {"success": True, "result": str(result) if result else None}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_elements(self, selector: str, by: str = "css") -> dict:
        """Get all elements matching selector"""
        if not self.driver:
            return {"success": False, "error": "No browser open"}
        
        by_method = {
            "css": By.CSS_SELECTOR,
            "xpath": By.XPATH,
            "id": By.ID,
            "tag": By.TAG_NAME
        }.get(by.lower(), By.CSS_SELECTOR)
        
        try:
            elements = self.driver.find_elements(by_method, selector)
            return {
                "success": True,
                "count": len(elements),
                "elements": [{"text": e.text[:100], "tag": e.tag_name} for e in elements[:20]]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def wait_for_element(self, selector: str, by: str = "css", timeout: int = 10) -> dict:
        """Wait for an element to appear"""
        if not self.driver:
            return {"success": False, "error": "No browser open"}
        
        by_method = {"css": By.CSS_SELECTOR, "xpath": By.XPATH, "id": By.ID}.get(by.lower(), By.CSS_SELECTOR)
        
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by_method, selector))
            )
            return {"success": True, "found": True, "text": element.text[:200]}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def go_back(self) -> dict:
        """Go back in browser history"""
        if not self.driver:
            return {"success": False, "error": "No browser open"}
        try:
            self.driver.back()
            return {"success": True, "url": self.driver.current_url}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def go_forward(self) -> dict:
        """Go forward in browser history"""
        if not self.driver:
            return {"success": False, "error": "No browser open"}
        try:
            self.driver.forward()
            return {"success": True, "url": self.driver.current_url}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def refresh(self) -> dict:
        """Refresh current page"""
        if not self.driver:
            return {"success": False, "error": "No browser open"}
        try:
            self.driver.refresh()
            return {"success": True, "url": self.driver.current_url}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def switch_tab(self, index: int) -> dict:
        """Switch to a different browser tab"""
        if not self.driver:
            return {"success": False, "error": "No browser open"}
        try:
            handles = self.driver.window_handles
            if 0 <= index < len(handles):
                self.driver.switch_to.window(handles[index])
                return {"success": True, "tab": index, "url": self.driver.current_url}
            return {"success": False, "error": f"Tab {index} not found. Have {len(handles)} tabs."}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def new_tab(self, url: Optional[str] = None) -> dict:
        """Open a new tab"""
        if not self.driver:
            return {"success": False, "error": "No browser open"}
        try:
            self.driver.execute_script("window.open('');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            if url:
                self.driver.get(url)
            return {"success": True, "url": url or "about:blank"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def close_tab(self) -> dict:
        """Close current tab"""
        if not self.driver:
            return {"success": False, "error": "No browser open"}
        try:
            self.driver.close()
            if self.driver.window_handles:
                self.driver.switch_to.window(self.driver.window_handles[-1])
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # --- Web Search (Multiple Providers with Fallback) ---
    
    def web_search(self, query: str, max_results: int = 5, provider: str = "auto") -> dict:
        """
        Search the web using multiple providers with automatic fallback.
        Providers: 'auto', 'tavily', 'google', 'brave', 'duckduckgo', 'bing'
        """
        providers_tried = []
        agent_working("amigos", f"Searching for: {query}", progress=50)
        
        # Auto mode: try providers in order until one works
        if provider == "auto":
            # Try Tavily AI Search first (best for LLMs, free tier)
            agent_working("amigos", "Trying Tavily AI Search...", progress=55)
            result = self._search_tavily(query, max_results)
            if result["success"]:
                result["provider"] = "tavily"
                agent_working("amigos", "Search successful (Tavily)", progress=80)
                return result
            providers_tried.append("tavily")
            
            # Try DuckDuckGo
            agent_working("amigos", "Trying DuckDuckGo...", progress=60)
            result = self._search_duckduckgo(query, max_results)
            if result["success"]:
                if "provider" not in result:
                    result["provider"] = "duckduckgo"
                agent_working("amigos", "Search successful (DuckDuckGo)", progress=80)
                return result
            providers_tried.append("duckduckgo")
            
            # Try Brave API if configured
            agent_working("amigos", "Trying Brave Search...", progress=65)
            result = self._search_brave_api(query, max_results)
            if result["success"]:
                result["provider"] = "brave"
                agent_working("amigos", "Search successful (Brave)", progress=80)
                return result
            providers_tried.append("brave")
            
            # Try HTTP-based Google search (no browser needed)
            agent_working("amigos", "Trying Google HTTP...", progress=70)
            result = self._search_google_http(query, max_results)
            if result["success"]:
                result["provider"] = "google_http"
                agent_working("amigos", "Search successful (Google)", progress=80)
                return result
            providers_tried.append("google_http")
            
            # Try Google via Selenium (needs browser)
            agent_working("amigos", "Trying Google Selenium...", progress=75)
            result = self._search_google_selenium(query, max_results)
            if result["success"]:
                result["provider"] = "google_selenium"
                agent_working("amigos", "Search successful (Google Selenium)", progress=80)
                return result
            providers_tried.append("google_selenium")
            
            # Try Bing via Selenium
            agent_working("amigos", "Trying Bing Selenium...", progress=78)
            result = self._search_bing_selenium(query, max_results)
            if result["success"]:
                result["provider"] = "bing_selenium"
                agent_working("amigos", "Search successful (Bing)", progress=80)
                return result
            providers_tried.append("bing_selenium")
            
            # Final attempt with Amigos AI if key exists
            if os.getenv("AMIGOS_API_KEY"):
                agent_working("amigos", "Trying Amigos AI Web Agent...", progress=85)
                result = self._search_amigos(query, max_results)
                if result["success"]:
                    result["provider"] = "amigos"
                    agent_working("amigos", "Search successful (Amigos)", progress=95)
                    return result
                providers_tried.append("amigos")
            
            return {"success": False, "error": f"All search providers failed. Tried: {providers_tried}"}
        
        # Specific provider requested
        if provider == "tavily":
            return self._search_tavily(query, max_results)
        elif provider == "google":
            return self._search_google_selenium(query, max_results)
        elif provider == "brave":
            return self._search_brave_api(query, max_results)
        elif provider == "duckduckgo":
            return self._search_duckduckgo(query, max_results)
        elif provider == "bing":
            return self._search_bing_selenium(query, max_results)
        else:
            return {"success": False, "error": f"Unknown provider: {provider}"}
    
    def _search_tavily(self, query: str, max_results: int = 5) -> dict:
        """Search using Tavily AI Search API (optimized for LLMs, free tier available)"""
        if not TAVILY_AVAILABLE:
            return {"success": False, "error": "tavily-python not installed"}
        
        try:
            api_key = os.environ.get("TAVILY_API_KEY", "")
            if not api_key:
                return {"success": False, "error": "TAVILY_API_KEY not set. Get free key at: https://tavily.com/"}
            
            client = TavilyClient(api_key=api_key)
            response = client.search(query=query, max_results=max_results)
            
            results = []
            for item in response.get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "href": item.get("url", ""),
                    "body": item.get("content", "")[:500]  # Truncate long content
                })
            
            if results:
                return {"success": True, "query": query, "results": results}
            else:
                return {"success": False, "error": "No results found"}
                
        except Exception as e:
            return {"success": False, "error": f"Tavily error: {str(e)}"}
    
    def _search_google_selenium(self, query: str, max_results: int = 5) -> dict:
        """Search Google using Selenium browser automation"""
        try:
            import urllib.parse
            
            # Ensure browser is open
            if not self.driver:
                self.open_browser(headless=True)
            
            if not self.driver:
                return {"success": False, "error": "Could not open browser"}
            
            # Go to Google
            search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&num={max_results + 5}"
            self.driver.get(search_url)
            time.sleep(2)
            
            results = []
            
            # Try to find search results
            try:
                # Main search results
                result_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.g")
                
                for elem in result_elements[:max_results]:
                    try:
                        title_elem = elem.find_element(By.CSS_SELECTOR, "h3")
                        link_elem = elem.find_element(By.CSS_SELECTOR, "a")
                        
                        # Get snippet/description
                        snippet = ""
                        try:
                            snippet_elem = elem.find_element(By.CSS_SELECTOR, "div.VwiC3b, span.aCOpRe")
                            snippet = snippet_elem.text
                        except:
                            pass
                        
                        results.append({
                            "title": title_elem.text,
                            "href": link_elem.get_attribute("href"),
                            "body": snippet
                        })
                    except:
                        continue
            except Exception as e:
                return {"success": False, "error": f"Failed to parse results: {str(e)}"}
            
            if results:
                return {"success": True, "query": query, "results": results}
            else:
                return {"success": False, "error": "No results found"}
                
        except Exception as e:
            return {"success": False, "error": f"Google search error: {str(e)}"}
    
    def _search_bing_selenium(self, query: str, max_results: int = 5) -> dict:
        """Search Bing using Selenium browser automation"""
        try:
            import urllib.parse
            
            if not self.driver:
                self.open_browser(headless=True)
            
            if not self.driver:
                return {"success": False, "error": "Could not open browser"}
            
            search_url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
            self.driver.get(search_url)
            time.sleep(2)
            
            results = []
            
            try:
                result_elements = self.driver.find_elements(By.CSS_SELECTOR, "li.b_algo")
                
                for elem in result_elements[:max_results]:
                    try:
                        title_elem = elem.find_element(By.CSS_SELECTOR, "h2 a")
                        
                        snippet = ""
                        try:
                            snippet_elem = elem.find_element(By.CSS_SELECTOR, "p")
                            snippet = snippet_elem.text
                        except:
                            pass
                        
                        results.append({
                            "title": title_elem.text,
                            "href": title_elem.get_attribute("href"),
                            "body": snippet
                        })
                    except:
                        continue
            except Exception as e:
                return {"success": False, "error": f"Failed to parse Bing results: {str(e)}"}
            
            if results:
                return {"success": True, "query": query, "results": results}
            else:
                return {"success": False, "error": "No Bing results found"}
                
        except Exception as e:
            return {"success": False, "error": f"Bing search error: {str(e)}"}
    
    def _search_amigos(self, query: str, max_results: int = 5) -> dict:
        """Search the web using Amigos Web Agent (high reliability)"""
        try:
            from tools.amigos_tools import amigos
            res = amigos.agent_task(f"Search for '{query}' and return the titles, URLs, and a brief description of the top {max_results} results as a JSON list.")
            if res.get("success"):
                data = res.get("data", {})
                # Normalize format to match other search results
                raw_results = data.get("results", []) or data.get("data", []) or []
                normalized = []
                for item in raw_results:
                    if isinstance(item, dict):
                        normalized.append({
                            "title": item.get("title") or item.get("name") or "Result",
                            "href": item.get("url") or item.get("href") or item.get("link"),
                            "body": item.get("description") or item.get("snippet") or item.get("body") or ""
                        })
                return {"success": True, "query": query, "results": normalized}
            return {"success": False, "error": res.get("error", "Unknown Amigos error")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _search_brave_api(self, query: str, max_results: int = 5) -> dict:
        """Search using Brave Search API (free tier available)"""
        try:
            # Check for API key in environment or config
            api_key = os.environ.get("BRAVE_API_KEY", "")
            
            if not api_key:
                return {"success": False, "error": "BRAVE_API_KEY not set. Get free key at: https://brave.com/search/api/"}
            
            if not REQUESTS_AVAILABLE:
                return {"success": False, "error": "requests library not available"}
            
            headers = {
                "Accept": "application/json",
                "X-Subscription-Token": api_key
            }
            
            response = requests.get(
                f"https://api.search.brave.com/res/v1/web/search?q={query}&count={max_results}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                results = []
                
                for item in data.get("web", {}).get("results", [])[:max_results]:
                    results.append({
                        "title": item.get("title", ""),
                        "href": item.get("url", ""),
                        "body": item.get("description", "")
                    })
                
                return {"success": True, "query": query, "results": results}
            else:
                return {"success": False, "error": f"Brave API error: {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": f"Brave search error: {str(e)}"}
    
    def _search_duckduckgo(self, query: str, max_results: int = 5) -> dict:
        """Search using DuckDuckGo (library or HTTP fallback)"""
        
        # Try DDGS library first
        if DDGS_AVAILABLE:
            try:
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    ddgs = DDGS()
                    results = list(ddgs.text(query, max_results=max_results))
                    if results:
                        return {"success": True, "query": query, "results": results}
            except Exception as e:
                print(f"[SEARCH] DDGS library error: {e}")
        
        # Fallback: Use DuckDuckGo HTML search (no API needed)
        try:
            import requests
            import urllib.parse
            from html import unescape
            import re
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            # DuckDuckGo HTML search
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                results = []
                # Parse results from HTML
                # Each result is in a div with class "result"
                result_pattern = r'<a rel="nofollow" class="result__a" href="([^"]+)"[^>]*>([^<]+)</a>.*?<a class="result__snippet"[^>]*>([^<]*)'
                matches = re.findall(result_pattern, response.text, re.DOTALL)
                
                for href, title, snippet in matches[:max_results]:
                    # Clean up the snippet
                    clean_snippet = re.sub(r'<[^>]+>', '', snippet)
                    clean_snippet = unescape(clean_snippet).strip()
                    
                    results.append({
                        "title": unescape(title).strip(),
                        "href": href,
                        "body": clean_snippet
                    })
                
                if results:
                    return {"success": True, "query": query, "results": results, "provider": "duckduckgo_html"}
            
        except Exception as e:
            print(f"[SEARCH] DuckDuckGo HTML fallback error: {e}")
        
        return {"success": False, "error": "DuckDuckGo search failed"}
    
    def _search_google_http(self, query: str, max_results: int = 5) -> dict:
        """Search Google using HTTP request (no browser needed, but may be rate limited)"""
        try:
            import requests
            import urllib.parse
            from html import unescape
            import re
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            
            # Google search URL
            url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&num={max_results + 5}"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                results = []
                html = response.text
                
                # Try to extract search results using common patterns
                # Pattern for titles and links in search results
                link_pattern = r'<a href="(/url\?q=|/search\?q=)?([^"&]+)[^"]*"[^>]*>(.*?)</a>'
                
                # Find all potential result blocks
                # Google wraps results in specific divs, but the structure changes
                # We'll look for h3 elements which typically contain result titles
                h3_pattern = r'<h3[^>]*>(.*?)</h3>'
                h3_matches = re.findall(h3_pattern, html, re.DOTALL)
                
                for h3_content in h3_matches[:max_results * 2]:
                    # Try to extract link from h3 content
                    link_match = re.search(r'<a[^>]+href="([^"]+)"[^>]*>([^<]+)', h3_content)
                    if link_match:
                        href = link_match.group(1)
                        title = unescape(link_match.group(2)).strip()
                        
                        # Clean up Google redirect URLs
                        if '/url?q=' in href:
                            href = href.split('/url?q=')[1].split('&')[0]
                        
                        # Skip non-result links
                        if href.startswith('/search') or 'google.com' in href:
                            continue
                        
                        # Try to find snippet near this result
                        snippet = ""
                        
                        results.append({
                            "title": title,
                            "href": urllib.parse.unquote(href),
                            "body": snippet
                        })
                        
                        if len(results) >= max_results:
                            break
                
                if results:
                    return {"success": True, "query": query, "results": results}
            
            return {"success": False, "error": f"Google HTTP search failed: {response.status_code}"}
            
        except Exception as e:
            return {"success": False, "error": f"Google HTTP error: {str(e)}"}
    
    def web_search_news(self, query: str, max_results: int = 5) -> dict:
        """Search news using available providers (DDG -> Google RSS -> Reddit RSS -> Selenium)"""
        agent_working("amigos", f"Searching news for: {query}", progress=50)
        
        # 1. Try DuckDuckGo News
        if DDGS_AVAILABLE:
            agent_working("amigos", "Trying DuckDuckGo News...", progress=55)
            try:
                with DDGS() as ddgs:
                    ddg_results = list(ddgs.news(query, max_results=max_results))
                if ddg_results:
                    return {"success": True, "query": query, "results": ddg_results, "provider": "duckduckgo"}
            except Exception as e:
                print(f"[NEWS] DDG failed: {e}")
        
        # 2. Try Google News RSS (No Browser Needed - Fast)
        try:
            import requests
            import xml.etree.ElementTree as ET
            import urllib.parse
            from html import unescape
            
            rss_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=en-US&gl=US&ceid=US:en"
            response = requests.get(rss_url, timeout=10)
            
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                items = root.findall(".//item")
                
                rss_results = []
                for item in items[:max_results]:
                    title = item.find("title").text if item.find("title") is not None else "No Title"
                    link = item.find("link").text if item.find("link") is not None else ""
                    pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
                    description = item.find("description").text if item.find("description") is not None else ""
                    
                    # Clean HTML from description if needed
                    clean_desc = description.replace("</a>", "").replace("<b>", "").replace("</b>", "")
                    if "<a" in clean_desc:
                        clean_desc = clean_desc.split("<a")[0]
                    
                    rss_results.append({
                        "title": unescape(title),
                        "href": link,
                        "body": unescape(clean_desc)[:200],
                        "date": pub_date,
                        "source": "Google News RSS"
                    })
                
                if rss_results:
                    return {"success": True, "query": query, "results": rss_results, "provider": "google_rss"}
        except Exception as e:
            print(f"[NEWS] Google RSS failed: {e}")

        # 3. Try Reddit RSS (Social Media "News")
        try:
            import requests
            import xml.etree.ElementTree as ET
            import urllib.parse
            
            # Search reddit for the query, sorted by new
            reddit_url = f"https://www.reddit.com/search.rss?q={urllib.parse.quote(query)}&sort=new"
            # Reddit requires a User-Agent
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.get(reddit_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                # Atom namespace
                ns = {'atom': 'http://www.w3.org/2005/Atom'}
                entries = root.findall("atom:entry", ns)
                if not entries:
                    entries = root.findall("{http://www.w3.org/2005/Atom}entry")
                
                reddit_results = []
                for entry in entries[:max_results]:
                    title_elem = entry.find("atom:title", ns)
                    if title_elem is None: title_elem = entry.find("{http://www.w3.org/2005/Atom}title")
                    title = title_elem.text if title_elem is not None else "No Title"
                    
                    link_elem = entry.find("atom:link", ns)
                    if link_elem is None: link_elem = entry.find("{http://www.w3.org/2005/Atom}link")
                    link = link_elem.attrib.get("href") if link_elem is not None else ""
                    
                    updated_elem = entry.find("atom:updated", ns)
                    if updated_elem is None: updated_elem = entry.find("{http://www.w3.org/2005/Atom}updated")
                    updated = updated_elem.text if updated_elem is not None else ""
                    
                    reddit_results.append({
                        "title": f"[Reddit] {title}",
                        "href": link,
                        "body": f"Reddit discussion found for {query}",
                        "date": updated,
                        "source": "Reddit"
                    })
                
                if reddit_results:
                    return {"success": True, "query": query, "results": reddit_results, "provider": "reddit_rss"}
        except Exception as e:
            print(f"[NEWS] Reddit RSS failed: {e}")
        
        # 4. Fall back to Google News via Selenium
        try:
            import urllib.parse
            
            if not self.driver:
                self.open_browser(headless=True)
            
            if self.driver:
                search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&tbm=nws"
                self.driver.get(search_url)
                time.sleep(2)
                
                results = []
                news_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.SoaBEf")
                
                for elem in news_elements[:max_results]:
                    try:
                        title_elem = elem.find_element(By.CSS_SELECTOR, "div.mCBkyc")
                        link_elem = elem.find_element(By.CSS_SELECTOR, "a")
                        
                        results.append({
                            "title": title_elem.text,
                            "href": link_elem.get_attribute("href"),
                            "body": "",
                            "source": "Google News (Browser)"
                        })
                    except:
                        continue
                
                if results:
                    return {"success": True, "query": query, "results": results, "provider": "google_selenium"}
        except Exception as e:
            print(f"[NEWS] Selenium failed: {e}")

        return {"success": False, "error": "No news providers available (DDG, Google RSS, Reddit, Selenium all failed)"}
    
    def fetch_url(self, url: str, timeout: int = 10) -> dict:
        """Fetch content from a URL (simple HTTP request)"""
        if not REQUESTS_AVAILABLE:
            return {"success": False, "error": "requests not installed"}
        
        try:
            response = requests.get(url, timeout=timeout, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            return {
                "success": True,
                "url": url,
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type", ""),
                "text": response.text[:5000]  # Limit response
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # --- Quick Actions (Open in Default Browser) ---
    
    def open_url_default_browser(self, url: str) -> dict:
        """Open URL in the user's default browser"""
        try:
            if platform.system() == "Windows":
                os.startfile(url)
            elif platform.system() == "Darwin":
                os.system(f"open '{url}'")
            else:
                os.system(f"xdg-open '{url}'")
            return {"success": True, "opened": url}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def google_search_in_browser(self, query: str) -> dict:
        """Open Google search in default browser"""
        import urllib.parse
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        return self.open_url_default_browser(url)
    
    # ═══════════════════════════════════════════════════════════════
    #           SOCIAL MEDIA INTERACTION TOOLS
    # ═══════════════════════════════════════════════════════════════
    
    def scroll_page(self, direction: str = "down", amount: int = 500) -> dict:
        """Scroll the page up or down"""
        if not self.driver:
            return {"success": False, "error": "No browser open"}
        try:
            scroll_amount = amount if direction.lower() == "down" else -amount
            self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
            return {"success": True, "scrolled": direction, "amount": amount}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_current_url(self) -> dict:
        """Get the current page URL"""
        if not self.driver:
            return {"success": False, "error": "No browser open"}
        try:
            return {"success": True, "url": self.driver.current_url, "title": self.driver.title}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def find_and_click_by_text(self, text: str, element_type: str = "*", partial: bool = True) -> dict:
        """Find and click an element containing specific text"""
        if not self.driver:
            return {"success": False, "error": "No browser open"}
        try:
            if partial:
                xpath = f"//{element_type}[contains(text(), '{text}')]"
            else:
                xpath = f"//{element_type}[text()='{text}']"
            
            element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            element.click()
            return {"success": True, "clicked_text": text}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def find_and_click_by_aria_label(self, label: str, partial: bool = True) -> dict:
        """Find and click element by aria-label (common for social media buttons)"""
        if not self.driver:
            return {"success": False, "error": "No browser open"}
        try:
            if partial:
                xpath = f"//*[contains(@aria-label, '{label}')]"
            else:
                xpath = f"//*[@aria-label='{label}']"
            
            element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            element.click()
            return {"success": True, "clicked_aria_label": label}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def read_post_content(self, platform: str = "auto") -> dict:
        """Read the main post content on current page"""
        if not self.driver:
            return {"success": False, "error": "No browser open"}
        
        try:
            url = self.driver.current_url.lower()
            post_content = ""
            author = ""
            
            # Facebook selectors
            if "facebook.com" in url or platform == "facebook":
                selectors = [
                    "[data-ad-preview='message']",
                    "[data-testid='post_message']",
                    ".userContent",
                    "[dir='auto']",
                    ".x1iorvi4"
                ]
                for sel in selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, sel)
                        if elements:
                            post_content = elements[0].text
                            break
                    except:
                        continue
            
            # Twitter/X selectors
            elif "twitter.com" in url or "x.com" in url or platform == "twitter":
                selectors = [
                    "[data-testid='tweetText']",
                    "article [lang]",
                    "[data-testid='tweet'] div[lang]"
                ]
                for sel in selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, sel)
                        if elements:
                            post_content = elements[0].text
                            break
                    except:
                        continue
            
            # Instagram selectors
            elif "instagram.com" in url or platform == "instagram":
                selectors = [
                    "h1._ap3a",
                    "span._ap3a",
                    "article span",
                    "._a9zs"
                ]
                for sel in selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, sel)
                        if elements:
                            post_content = elements[0].text
                            break
                    except:
                        continue
            
            # LinkedIn selectors
            elif "linkedin.com" in url or platform == "linkedin":
                selectors = [
                    ".feed-shared-update-v2__description",
                    ".feed-shared-text",
                    ".break-words",
                    "[data-test-id='main-feed-activity-card__commentary']"
                ]
                for sel in selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, sel)
                        if elements:
                            post_content = elements[0].text
                            break
                    except:
                        continue
            
            # TikTok selectors
            elif "tiktok.com" in url or platform == "tiktok":
                selectors = [
                    "[data-e2e='browse-video-desc']",
                    ".tiktok-j2a19r-SpanText",
                    "[data-e2e='video-desc']"
                ]
                for sel in selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, sel)
                        if elements:
                            post_content = elements[0].text
                            break
                    except:
                        continue
            
            # YouTube selectors
            elif "youtube.com" in url or platform == "youtube":
                selectors = [
                    "#title h1",
                    "h1.ytd-video-primary-info-renderer",
                    "#description-inner"
                ]
                for sel in selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, sel)
                        if elements:
                            post_content = elements[0].text
                            break
                    except:
                        continue
            
            if post_content:
                return {
                    "success": True,
                    "platform": platform if platform != "auto" else url.split(".com")[0].split("//")[-1],
                    "content": post_content[:2000],
                    "url": self.driver.current_url
                }
            else:
                return {"success": False, "error": "Could not find post content. Page may need to load or selector not matched."}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def like_post(self, platform: str = "auto") -> dict:
        """Like/Heart the current post on social media"""
        if not self.driver:
            return {"success": False, "error": "No browser open"}
        
        try:
            url = self.driver.current_url.lower()
            
            # Facebook like button
            if "facebook.com" in url or platform == "facebook":
                like_selectors = [
                    "[aria-label='Like']",
                    "[aria-label='like']",
                    "[data-testid='like-button']",
                    "div[aria-label*='Like']",
                    "span[aria-label*='Like']"
                ]
                for sel in like_selectors:
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, sel)
                        element.click()
                        return {"success": True, "action": "liked", "platform": "facebook"}
                    except:
                        continue
            
            # Twitter/X like button
            elif "twitter.com" in url or "x.com" in url or platform == "twitter":
                like_selectors = [
                    "[data-testid='like']",
                    "[aria-label*='Like']",
                    "[aria-label*='like']"
                ]
                for sel in like_selectors:
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, sel)
                        element.click()
                        return {"success": True, "action": "liked", "platform": "twitter/x"}
                    except:
                        continue
            
            # Instagram like button
            elif "instagram.com" in url or platform == "instagram":
                like_selectors = [
                    "[aria-label='Like']",
                    "[aria-label='like']",
                    "svg[aria-label='Like']",
                    "span svg[aria-label='Like']"
                ]
                for sel in like_selectors:
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, sel)
                        element.click()
                        return {"success": True, "action": "liked", "platform": "instagram"}
                    except:
                        continue
            
            # LinkedIn like button
            elif "linkedin.com" in url or platform == "linkedin":
                like_selectors = [
                    "[aria-label*='Like']",
                    "button[aria-label*='like']",
                    ".react-button__trigger"
                ]
                for sel in like_selectors:
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, sel)
                        element.click()
                        return {"success": True, "action": "liked", "platform": "linkedin"}
                    except:
                        continue
            
            # TikTok like button
            elif "tiktok.com" in url or platform == "tiktok":
                like_selectors = [
                    "[data-e2e='like-icon']",
                    "[data-e2e='browse-like-icon']",
                    "span[data-e2e='like-icon']"
                ]
                for sel in like_selectors:
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, sel)
                        element.click()
                        return {"success": True, "action": "liked", "platform": "tiktok"}
                    except:
                        continue
            
            # YouTube like button
            elif "youtube.com" in url or platform == "youtube":
                like_selectors = [
                    "#top-level-buttons-computed ytd-toggle-button-renderer:first-child button",
                    "[aria-label*='like this video']",
                    "ytd-toggle-button-renderer button[aria-pressed]"
                ]
                for sel in like_selectors:
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, sel)
                        element.click()
                        return {"success": True, "action": "liked", "platform": "youtube"}
                    except:
                        continue
            
            return {"success": False, "error": "Could not find like button. Make sure you're on a post page."}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def follow_user(self, platform: str = "auto") -> dict:
        """Follow the user/account on current page"""
        if not self.driver:
            return {"success": False, "error": "No browser open"}
        
        try:
            url = self.driver.current_url.lower()
            
            # Facebook follow button
            if "facebook.com" in url or platform == "facebook":
                follow_selectors = [
                    "[aria-label='Follow']",
                    "[aria-label='follow']",
                    "div[aria-label*='Follow']",
                    "//span[text()='Follow']",
                    "//div[text()='Follow']"
                ]
                for sel in follow_selectors:
                    try:
                        if sel.startswith("//"):
                            element = self.driver.find_element(By.XPATH, sel)
                        else:
                            element = self.driver.find_element(By.CSS_SELECTOR, sel)
                        element.click()
                        return {"success": True, "action": "followed", "platform": "facebook"}
                    except:
                        continue
            
            # Twitter/X follow button
            elif "twitter.com" in url or "x.com" in url or platform == "twitter":
                follow_selectors = [
                    "[data-testid$='-follow']",
                    "[aria-label*='Follow @']",
                    "//span[text()='Follow']",
                    "[role='button'][data-testid*='follow']"
                ]
                for sel in follow_selectors:
                    try:
                        if sel.startswith("//"):
                            element = self.driver.find_element(By.XPATH, sel)
                        else:
                            element = self.driver.find_element(By.CSS_SELECTOR, sel)
                        element.click()
                        return {"success": True, "action": "followed", "platform": "twitter/x"}
                    except:
                        continue
            
            # Instagram follow button
            elif "instagram.com" in url or platform == "instagram":
                follow_selectors = [
                    "button:contains('Follow')",
                    "//button[text()='Follow']",
                    "//div[text()='Follow']",
                    "[aria-label='Follow']"
                ]
                for sel in follow_selectors:
                    try:
                        if sel.startswith("//"):
                            element = self.driver.find_element(By.XPATH, sel)
                        else:
                            element = self.driver.find_element(By.CSS_SELECTOR, sel)
                        element.click()
                        return {"success": True, "action": "followed", "platform": "instagram"}
                    except:
                        continue
            
            # LinkedIn connect button
            elif "linkedin.com" in url or platform == "linkedin":
                follow_selectors = [
                    "[aria-label*='Follow']",
                    "[aria-label*='Connect']",
                    "//span[text()='Follow']",
                    "//span[text()='Connect']",
                    "button[aria-label*='follow']"
                ]
                for sel in follow_selectors:
                    try:
                        if sel.startswith("//"):
                            element = self.driver.find_element(By.XPATH, sel)
                        else:
                            element = self.driver.find_element(By.CSS_SELECTOR, sel)
                        element.click()
                        return {"success": True, "action": "followed/connected", "platform": "linkedin"}
                    except:
                        continue
            
            # TikTok follow button
            elif "tiktok.com" in url or platform == "tiktok":
                follow_selectors = [
                    "[data-e2e='follow-button']",
                    "[data-e2e='browse-follow']",
                    "//button[contains(text(), 'Follow')]"
                ]
                for sel in follow_selectors:
                    try:
                        if sel.startswith("//"):
                            element = self.driver.find_element(By.XPATH, sel)
                        else:
                            element = self.driver.find_element(By.CSS_SELECTOR, sel)
                        element.click()
                        return {"success": True, "action": "followed", "platform": "tiktok"}
                    except:
                        continue
            
            # YouTube subscribe button
            elif "youtube.com" in url or platform == "youtube":
                follow_selectors = [
                    "#subscribe-button button",
                    "[aria-label*='Subscribe']",
                    "ytd-subscribe-button-renderer button"
                ]
                for sel in follow_selectors:
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, sel)
                        element.click()
                        return {"success": True, "action": "subscribed", "platform": "youtube"}
                    except:
                        continue
            
            return {"success": False, "error": "Could not find follow/subscribe button. Make sure you're on a profile or post page."}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def open_comment_box(self, platform: str = "auto") -> dict:
        """Open/focus the comment input box"""
        if not self.driver:
            return {"success": False, "error": "No browser open"}
        
        try:
            url = self.driver.current_url.lower()
            
            # Facebook comment box
            if "facebook.com" in url or platform == "facebook":
                comment_selectors = [
                    "[aria-label='Write a comment']",
                    "[aria-label='Write a comment...']",
                    "[placeholder*='Write a comment']",
                    "[data-testid='post_message_comment_box']",
                    "div[contenteditable='true'][role='textbox']"
                ]
                for sel in comment_selectors:
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, sel)
                        element.click()
                        return {"success": True, "action": "comment_box_opened", "platform": "facebook"}
                    except:
                        continue
            
            # Twitter/X reply box - first click reply button
            elif "twitter.com" in url or "x.com" in url or platform == "twitter":
                reply_selectors = [
                    "[data-testid='reply']",
                    "[aria-label*='Reply']",
                    "[aria-label*='reply']"
                ]
                for sel in reply_selectors:
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, sel)
                        element.click()
                        time.sleep(1)  # Wait for reply box to open
                        return {"success": True, "action": "reply_box_opened", "platform": "twitter/x"}
                    except:
                        continue
            
            # Instagram comment box
            elif "instagram.com" in url or platform == "instagram":
                comment_selectors = [
                    "[aria-label='Add a comment…']",
                    "[placeholder='Add a comment…']",
                    "textarea[aria-label*='comment']"
                ]
                for sel in comment_selectors:
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, sel)
                        element.click()
                        return {"success": True, "action": "comment_box_opened", "platform": "instagram"}
                    except:
                        continue
            
            # LinkedIn comment box
            elif "linkedin.com" in url or platform == "linkedin":
                comment_selectors = [
                    "[aria-label*='comment']",
                    ".comment-button",
                    "[placeholder*='Add a comment']"
                ]
                for sel in comment_selectors:
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, sel)
                        element.click()
                        return {"success": True, "action": "comment_box_opened", "platform": "linkedin"}
                    except:
                        continue
            
            # TikTok comment box
            elif "tiktok.com" in url or platform == "tiktok":
                comment_selectors = [
                    "[data-e2e='comment-input']",
                    "[placeholder*='Add comment']"
                ]
                for sel in comment_selectors:
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, sel)
                        element.click()
                        return {"success": True, "action": "comment_box_opened", "platform": "tiktok"}
                    except:
                        continue
            
            # YouTube comment box
            elif "youtube.com" in url or platform == "youtube":
                comment_selectors = [
                    "#simplebox-placeholder",
                    "#placeholder-area",
                    "[placeholder='Add a comment...']"
                ]
                for sel in comment_selectors:
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, sel)
                        element.click()
                        time.sleep(0.5)
                        return {"success": True, "action": "comment_box_opened", "platform": "youtube"}
                    except:
                        continue
            
            return {"success": False, "error": "Could not find comment box. Make sure you're on a post page."}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def write_comment(self, comment: str, platform: str = "auto", submit: bool = True) -> dict:
        """Write and optionally submit a comment on the current post"""
        if not self.driver:
            return {"success": False, "error": "No browser open"}
        
        try:
            url = self.driver.current_url.lower()
            
            # First try to open the comment box
            self.open_comment_box(platform)
            time.sleep(1)
            
            # Facebook comment
            if "facebook.com" in url or platform == "facebook":
                input_selectors = [
                    "div[contenteditable='true'][role='textbox']",
                    "[aria-label='Write a comment']",
                    "[data-testid='post_message_comment_box'] div[contenteditable='true']"
                ]
                for sel in input_selectors:
                    try:
                        element = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                        )
                        element.click()
                        element.send_keys(comment)
                        if submit:
                            element.send_keys(Keys.RETURN)
                        return {"success": True, "action": "commented", "comment": comment, "platform": "facebook"}
                    except:
                        continue
            
            # Twitter/X reply
            elif "twitter.com" in url or "x.com" in url or platform == "twitter":
                input_selectors = [
                    "[data-testid='tweetTextarea_0']",
                    "div[role='textbox'][data-testid='tweetTextarea_0']",
                    "[aria-label='Post text']"
                ]
                for sel in input_selectors:
                    try:
                        element = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                        )
                        element.click()
                        element.send_keys(comment)
                        if submit:
                            # Find and click Reply/Post button
                            post_btn = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='tweetButton']")
                            post_btn.click()
                        return {"success": True, "action": "replied", "comment": comment, "platform": "twitter/x"}
                    except:
                        continue
            
            # Instagram comment
            elif "instagram.com" in url or platform == "instagram":
                input_selectors = [
                    "textarea[aria-label*='comment']",
                    "[aria-label='Add a comment…']",
                    "form textarea"
                ]
                for sel in input_selectors:
                    try:
                        element = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                        )
                        element.click()
                        element.send_keys(comment)
                        if submit:
                            # Find and click Post button
                            post_btn = self.driver.find_element(By.XPATH, "//button[text()='Post']")
                            post_btn.click()
                        return {"success": True, "action": "commented", "comment": comment, "platform": "instagram"}
                    except:
                        continue
            
            # LinkedIn comment
            elif "linkedin.com" in url or platform == "linkedin":
                input_selectors = [
                    ".ql-editor",
                    "[aria-label*='comment']",
                    "div[contenteditable='true']"
                ]
                for sel in input_selectors:
                    try:
                        element = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                        )
                        element.click()
                        element.send_keys(comment)
                        if submit:
                            post_btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                            post_btn.click()
                        return {"success": True, "action": "commented", "comment": comment, "platform": "linkedin"}
                    except:
                        continue
            
            # TikTok comment
            elif "tiktok.com" in url or platform == "tiktok":
                input_selectors = [
                    "[data-e2e='comment-input']",
                    "div[contenteditable='true']"
                ]
                for sel in input_selectors:
                    try:
                        element = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                        )
                        element.click()
                        element.send_keys(comment)
                        if submit:
                            element.send_keys(Keys.RETURN)
                        return {"success": True, "action": "commented", "comment": comment, "platform": "tiktok"}
                    except:
                        continue
            
            # YouTube comment
            elif "youtube.com" in url or platform == "youtube":
                input_selectors = [
                    "#contenteditable-root",
                    "div#contenteditable-root[contenteditable='true']"
                ]
                for sel in input_selectors:
                    try:
                        element = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                        )
                        element.click()
                        element.send_keys(comment)
                        if submit:
                            # Find and click Comment button
                            post_btn = self.driver.find_element(By.CSS_SELECTOR, "#submit-button")
                            post_btn.click()
                        return {"success": True, "action": "commented", "comment": comment, "platform": "youtube"}
                    except:
                        continue
            
            return {"success": False, "error": "Could not write comment. Make sure you're logged in and on a post page."}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def follow_back_comment(self, platform: str = "auto") -> dict:
        """Leave a 'follow back' comment on the current post"""
        follow_back_messages = [
            "Great content! Follow back? 🙏 #darrellbuttigieg #thesoldiersdream",
            "Love this! Let's connect - follow back! 💪 #darrellbuttigieg #thesoldiersdream",
            "Amazing post! Follow back please 🔥 #darrellbuttigieg #thesoldiersdream",
            "This is fire! 🔥 Follow back? #darrellbuttigieg #thesoldiersdream",
            "Nice content! Following - follow back! 🤝 #darrellbuttigieg #thesoldiersdream"
        ]
        import random
        message = random.choice(follow_back_messages)
        return self.write_comment(message, platform, submit=True)
    
    def engage_with_post(self, like: bool = True, follow: bool = True, comment: str = None) -> dict:
        """Full engagement: like, follow, and optionally comment on a post"""
        if not self.driver:
            return {"success": False, "error": "No browser open"}
        
        results = {"success": True, "actions": []}
        
        try:
            # Like the post
            if like:
                like_result = self.like_post()
                results["actions"].append({"like": like_result})
                time.sleep(1)
            
            # Follow the user
            if follow:
                follow_result = self.follow_user()
                results["actions"].append({"follow": follow_result})
                time.sleep(1)
            
            # Leave a comment
            if comment:
                comment_result = self.write_comment(comment)
                results["actions"].append({"comment": comment_result})
            
            return results
            
        except Exception as e:
            return {"success": False, "error": str(e), "partial_actions": results.get("actions", [])}
    
    def get_visible_posts(self, max_posts: int = 5) -> dict:
        """Get a list of visible posts on the current feed"""
        if not self.driver:
            return {"success": False, "error": "No browser open"}
        
        try:
            url = self.driver.current_url.lower()
            posts = []
            
            # Facebook posts
            if "facebook.com" in url:
                post_elements = self.driver.find_elements(By.CSS_SELECTOR, "[data-pagelet^='FeedUnit']")[:max_posts]
                for i, post in enumerate(post_elements):
                    try:
                        text = post.text[:200] if post.text else "No text"
                        posts.append({"index": i, "preview": text})
                    except:
                        continue
            
            # Twitter/X posts
            elif "twitter.com" in url or "x.com" in url:
                post_elements = self.driver.find_elements(By.CSS_SELECTOR, "article[data-testid='tweet']")[:max_posts]
                for i, post in enumerate(post_elements):
                    try:
                        text = post.text[:200] if post.text else "No text"
                        posts.append({"index": i, "preview": text})
                    except:
                        continue
            
            # Instagram posts
            elif "instagram.com" in url:
                post_elements = self.driver.find_elements(By.CSS_SELECTOR, "article")[:max_posts]
                for i, post in enumerate(post_elements):
                    try:
                        text = post.text[:200] if post.text else "No text"
                        posts.append({"index": i, "preview": text})
                    except:
                        continue
            
            return {"success": True, "count": len(posts), "posts": posts}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ═══════════════════════════════════════════════════════════════
    #           FACEBOOK GROUP SPECIFIC TOOLS
    # ═══════════════════════════════════════════════════════════════
    
    # Saved Facebook Groups for quick access
    FACEBOOK_GROUPS = {
        "main": "https://www.facebook.com/groups/26982601774687430",
        "default": "https://www.facebook.com/groups/26982601774687430",
        "preferred": "https://www.facebook.com/groups/26982601774687430",
        "profile_groups": "https://www.facebook.com/AmigosBrenton/groups",
        "my_groups": "https://www.facebook.com/AmigosBrenton/groups",
        "amigos_brenton": "https://www.facebook.com/AmigosBrenton/groups",
        "darrells_groups": "https://www.facebook.com/AmigosBrenton/groups"
    }
    
    def open_facebook_group(self, group_id: str = "main") -> dict:
        """Open a saved Facebook group or by URL/ID"""
        try:
            # Check if it's a saved group name
            if group_id in self.FACEBOOK_GROUPS:
                url = self.FACEBOOK_GROUPS[group_id]
            elif group_id.startswith("http"):
                url = group_id
            elif group_id.isdigit():
                url = f"https://www.facebook.com/groups/{group_id}"
            else:
                url = f"https://www.facebook.com/groups/{group_id}"
            
            # Open in default browser
            result = self.open_url_default_browser(url)
            if result.get("success"):
                return {"success": True, "opened": url, "group": group_id}
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def open_facebook_group_automated(self, group_id: str = "main") -> dict:
        """Open Facebook group in automated browser for interaction"""
        try:
            # Check if it's a saved group name
            if group_id in self.FACEBOOK_GROUPS:
                url = self.FACEBOOK_GROUPS[group_id]
            elif group_id.startswith("http"):
                url = group_id
            elif group_id.isdigit():
                url = f"https://www.facebook.com/groups/{group_id}"
            else:
                url = f"https://www.facebook.com/groups/{group_id}"
            
            # Open browser if not already open
            if not self.driver:
                browser_result = self.open_browser()
                if not browser_result.get("success"):
                    return browser_result
            
            try:
                self.driver.get(url)
            except Exception as e:
                if "invalid session id" in str(e).lower() or "no such window" in str(e).lower():
                    print("[FACEBOOK] Invalid session detected, restarting browser...")
                    self.driver = None
                    browser_result = self.open_browser()
                    if not browser_result.get("success"):
                        return browser_result
                    self.driver.get(url)
                else:
                    raise e

            time.sleep(3)  # Wait for page to load
            
            return {
                "success": True,
                "url": url,
                "title": self.driver.title,
                "group": group_id,
                "note": "Facebook group opened. You may need to log in if not already."
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_facebook_group_posts(self, max_posts: int = 10) -> dict:
        """Get posts from the current Facebook group page"""
        if not self.driver:
            return {"success": False, "error": "No browser open. Use open_facebook_group_automated first."}
        
        try:
            url = self.driver.current_url.lower()
            if "facebook.com/groups" not in url:
                return {"success": False, "error": "Not on a Facebook group page"}
            
            # Scroll to load more posts
            for _ in range(3):
                self.driver.execute_script("window.scrollBy(0, 1000);")
                time.sleep(1)
            
            posts = []
            
            # Various selectors for Facebook group posts
            post_selectors = [
                "[data-pagelet^='GroupFeed'] [role='article']",
                "[role='feed'] [role='article']",
                "[data-pagelet^='FeedUnit']",
                "div[class*='x1yztbdb']"
            ]
            
            for selector in post_selectors:
                try:
                    post_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)[:max_posts]
                    if post_elements:
                        for i, post in enumerate(post_elements):
                            try:
                                post_text = post.text[:500] if post.text else ""
                                # Try to find author name
                                author = ""
                                try:
                                    author_el = post.find_element(By.CSS_SELECTOR, "a[role='link'] strong, h2 a, span.x193iq5w")
                                    author = author_el.text
                                except:
                                    pass
                                
                                posts.append({
                                    "index": i,
                                    "author": author,
                                    "preview": post_text[:300],
                                    "full_text": post_text
                                })
                            except:
                                continue
                        break
                except:
                    continue
            
            return {
                "success": True,
                "group_url": self.driver.current_url,
                "count": len(posts),
                "posts": posts
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def like_facebook_group_post(self, post_index: int = 0) -> dict:
        """Like a specific post in Facebook group by index"""
        if not self.driver:
            return {"success": False, "error": "No browser open"}
        
        try:
            # Find all posts
            post_selectors = [
                "[role='feed'] [role='article']",
                "[data-pagelet^='FeedUnit']"
            ]
            
            for selector in post_selectors:
                try:
                    posts = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if posts and post_index < len(posts):
                        post = posts[post_index]
                        
                        # Find like button within post
                        like_selectors = [
                            "[aria-label='Like']",
                            "[aria-label='like']",
                            "div[aria-label*='Like']",
                            "span[aria-label*='Like']"
                        ]
                        
                        for like_sel in like_selectors:
                            try:
                                like_btn = post.find_element(By.CSS_SELECTOR, like_sel)
                                like_btn.click()
                                return {"success": True, "action": "liked", "post_index": post_index}
                            except:
                                continue
                except:
                    continue
            
            return {"success": False, "error": f"Could not find like button for post {post_index}"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def comment_on_facebook_group_post(self, comment: str, post_index: int = 0) -> dict:
        """Comment on a specific post in Facebook group"""
        if not self.driver:
            return {"success": False, "error": "No browser open"}
        
        try:
            # Find all posts
            post_selectors = [
                "[role='feed'] [role='article']",
                "[data-pagelet^='FeedUnit']"
            ]
            
            for selector in post_selectors:
                try:
                    posts = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if posts and post_index < len(posts):
                        post = posts[post_index]
                        
                        # Click comment button first
                        comment_btn_selectors = [
                            "[aria-label='Leave a comment']",
                            "[aria-label='Comment']",
                            "div[aria-label*='Comment']"
                        ]
                        
                        for btn_sel in comment_btn_selectors:
                            try:
                                comment_btn = post.find_element(By.CSS_SELECTOR, btn_sel)
                                comment_btn.click()
                                time.sleep(1)
                                break
                            except:
                                continue
                        
                        # Find comment input
                        comment_input_selectors = [
                            "div[contenteditable='true'][role='textbox']",
                            "[aria-label='Write a comment']",
                            "[placeholder*='Write a comment']"
                        ]
                        
                        for input_sel in comment_input_selectors:
                            try:
                                comment_input = WebDriverWait(self.driver, 5).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, input_sel))
                                )
                                comment_input.click()
                                comment_input.send_keys(comment)
                                time.sleep(0.5)
                                comment_input.send_keys(Keys.RETURN)
                                return {"success": True, "action": "commented", "comment": comment, "post_index": post_index}
                            except:
                                continue
                except:
                    continue
            
            return {"success": False, "error": f"Could not comment on post {post_index}"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_facebook_group_post(self, content: str) -> dict:
        """Create a new post in the current Facebook group"""
        if not self.driver:
            return {"success": False, "error": "No browser open"}
        
        try:
            url = self.driver.current_url.lower()
            if "facebook.com/groups" not in url:
                return {"success": False, "error": "Not on a Facebook group page"}
            
            # Click on "Write something..." box
            create_post_selectors = [
                "[aria-label='Write something...']",
                "[aria-label='Create a public post…']",
                "[aria-label='Write something']",
                "div[role='button'][tabindex='0']",
                "span:contains('Write something')"
            ]
            
            for sel in create_post_selectors:
                try:
                    if ":contains" in sel:
                        # Use XPath for text matching
                        create_btn = self.driver.find_element(By.XPATH, "//span[contains(text(), 'Write something')]")
                    else:
                        create_btn = self.driver.find_element(By.CSS_SELECTOR, sel)
                    create_btn.click()
                    time.sleep(2)
                    break
                except:
                    continue
            
            # Find the post input box (modal opens)
            post_input_selectors = [
                "div[contenteditable='true'][role='textbox']",
                "[aria-label='Create a public post…']",
                "[aria-label*='What']",
                "div[data-lexical-editor='true']"
            ]
            
            for input_sel in post_input_selectors:
                try:
                    post_input = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, input_sel))
                    )
                    post_input.click()
                    post_input.send_keys(content)
                    time.sleep(1)
                    
                    # Find and click Post button
                    post_btn_selectors = [
                        "[aria-label='Post']",
                        "div[aria-label='Post']",
                        "//span[text()='Post']",
                        "//div[text()='Post']"
                    ]
                    
                    for btn_sel in post_btn_selectors:
                        try:
                            if btn_sel.startswith("//"):
                                post_btn = self.driver.find_element(By.XPATH, btn_sel)
                            else:
                                post_btn = self.driver.find_element(By.CSS_SELECTOR, btn_sel)
                            post_btn.click()
                            return {"success": True, "action": "posted", "content": content[:100] + "..."}
                        except:
                            continue
                    
                    return {"success": True, "action": "drafted", "content": content[:100], "note": "Content typed but Post button not clicked. Click manually."}
                except:
                    continue
            
            return {"success": False, "error": "Could not find post creation area"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def engage_facebook_group_posts(self, max_posts: int = 5, like: bool = True, comment: bool = True) -> dict:
        """Auto-engage with multiple posts in a Facebook group"""
        if not self.driver:
            return {"success": False, "error": "No browser open"}
        
        results = {"success": True, "engaged": [], "errors": []}
        
        follow_back_comments = [
            "Great post! Follow back? 🙏 #darrellbuttigieg #thesoldiersdream",
            "Love this! 💪 #darrellbuttigieg #thesoldiersdream",
            "Nice share! 🔥 #darrellbuttigieg #thesoldiersdream",
            "Thanks for sharing! 👍 #darrellbuttigieg #thesoldiersdream",
            "Awesome content! 🌟 #darrellbuttigieg #thesoldiersdream"
        ]
        
        import random
        
        try:
            for i in range(max_posts):
                engaged = {"post_index": i}
                
                # Like the post
                if like:
                    like_result = self.like_facebook_group_post(i)
                    engaged["liked"] = like_result.get("success", False)
                    time.sleep(1)
                
                # Comment on the post
                if comment:
                    comment_text = random.choice(follow_back_comments)
                    comment_result = self.comment_on_facebook_group_post(comment_text, i)
                    engaged["commented"] = comment_result.get("success", False)
                    engaged["comment_text"] = comment_text
                    time.sleep(2)
                
                results["engaged"].append(engaged)
                
                # Scroll to next post
                self.driver.execute_script("window.scrollBy(0, 500);")
                time.sleep(1)
            
            return results
            
        except Exception as e:
            results["errors"].append(str(e))
            return results
    
    def scroll_facebook_feed(self, times: int = 3) -> dict:
        """Scroll the Facebook feed to load more posts"""
        if not self.driver:
            return {"success": False, "error": "No browser open"}
        
        try:
            for i in range(times):
                self.driver.execute_script("window.scrollBy(0, 800);")
                time.sleep(1.5)
            
            return {"success": True, "scrolled": times, "note": "Feed scrolled to load more posts"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def full_facebook_engagement(self, max_posts: int = 10, scroll_times: int = 5) -> dict:
        """
        Complete Facebook group engagement: scrolls through page, likes, follows, and comments on every post.
        This is the MASTER engagement tool for viral growth.
        Automatically opens browser and navigates to main group if not already running.
        """
        # Auto-open browser and navigate to main group if not already open
        if not self.driver:
            print("[ENGAGE] Browser not open, auto-opening...")
            browser_result = self.open_browser()
            if not browser_result.get("success"):
                return {"success": False, "error": f"Failed to open browser: {browser_result.get('error')}"}
            
            # Navigate to main group
            group_open = self.open_facebook_group_automated(group_id="main")
            if not group_open.get("success"):
                return {"success": False, "error": f"Failed to open Facebook group: {group_open.get('error')}"}
            
            print("[ENGAGE] Browser opened and navigated to main group")
        
        import random
        
        # Owner's engagement comments - always includes hashtags
        engagement_comments = [
            "Amazing post! 🔥 Follow back? #darrellbuttigieg #thesoldiersdream",
            "Love this content! 💪 Let's connect! #darrellbuttigieg #thesoldiersdream",
            "Great share! 🙌 Follow for follow? #darrellbuttigieg #thesoldiersdream",
            "This is gold! ⭐ #darrellbuttigieg #thesoldiersdream",
            "Inspiring! Keep it up! 💯 #darrellbuttigieg #thesoldiersdream",
            "Nice one! 👏 Following you! #darrellbuttigieg #thesoldiersdream",
            "Awesome! Let's support each other 🤝 #darrellbuttigieg #thesoldiersdream",
            "Quality content right here! 🌟 #darrellbuttigieg #thesoldiersdream",
            "Thanks for sharing this! 🙏 #darrellbuttigieg #thesoldiersdream",
            "This resonates with me! 💡 #darrellbuttigieg #thesoldiersdream",
            "Powerful message! 💪 #darrellbuttigieg #thesoldiersdream",
            "Exactly what I needed to see today! ✨ #darrellbuttigieg #thesoldiersdream"
        ]
        
        results = {
            "success": True,
            "total_posts_found": 0,
            "posts_liked": 0,
            "posts_commented": 0,
            "users_followed": 0,
            "scroll_count": 0,
            "engagement_log": [],
            "errors": []
        }
        
        try:
            # First scroll to load posts
            print("[ENGAGE] Starting full Facebook engagement...")
            
            for scroll in range(scroll_times):
                self.driver.execute_script("window.scrollBy(0, 1000);")
                time.sleep(2)
                results["scroll_count"] += 1
                print(f"[ENGAGE] Scrolled {scroll + 1}/{scroll_times}")
            
            # Scroll back to top
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            
            # Find all posts
            post_selectors = [
                "[role='feed'] [role='article']",
                "[data-pagelet^='FeedUnit']",
                "[data-pagelet^='GroupFeed'] [role='article']",
                "div[class*='x1yztbdb'][class*='x1n2onr6']"
            ]
            
            posts = []
            for selector in post_selectors:
                try:
                    posts = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if posts:
                        print(f"[ENGAGE] Found {len(posts)} posts with selector: {selector}")
                        break
                except:
                    continue
            
            results["total_posts_found"] = len(posts)
            
            if not posts:
                results["errors"].append("No posts found on page")
                return results
            
            # Process each post (up to max_posts)
            for i, post in enumerate(posts[:max_posts]):
                post_log = {"index": i, "actions": []}
                
                try:
                    # Scroll post into view
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", post)
                    time.sleep(1.5)
                    
                    # ========== 1. LIKE THE POST ==========
                    like_selectors = [
                        "[aria-label='Like']",
                        "[aria-label='like']",
                        "div[aria-label*='Like']",
                        "span[aria-label*='Like']",
                        "[data-testid='like_button']"
                    ]
                    
                    liked = False
                    for like_sel in like_selectors:
                        try:
                            like_btn = post.find_element(By.CSS_SELECTOR, like_sel)
                            # Check if not already liked
                            aria_pressed = like_btn.get_attribute("aria-pressed")
                            if aria_pressed != "true":
                                like_btn.click()
                                liked = True
                                results["posts_liked"] += 1
                                post_log["actions"].append("liked")
                                print(f"[ENGAGE] Post {i}: Liked ✓")
                                time.sleep(0.5)
                            else:
                                post_log["actions"].append("already_liked")
                            break
                        except:
                            continue
                    
                    # ========== 2. FOLLOW THE USER ==========
                    follow_selectors = [
                        "[aria-label='Follow']",
                        "[aria-label='follow']",
                        "div[aria-label*='Follow']",
                        "a[aria-label*='Follow']",
                        "//span[text()='Follow']",
                        "//div[text()='Follow']"
                    ]
                    
                    followed = False
                    for follow_sel in follow_selectors:
                        try:
                            if follow_sel.startswith("//"):
                                follow_btn = post.find_element(By.XPATH, follow_sel)
                            else:
                                follow_btn = post.find_element(By.CSS_SELECTOR, follow_sel)
                            follow_btn.click()
                            followed = True
                            results["users_followed"] += 1
                            post_log["actions"].append("followed")
                            print(f"[ENGAGE] Post {i}: Followed user ✓")
                            time.sleep(0.5)
                            break
                        except:
                            continue
                    
                    # ========== 3. COMMENT ON THE POST ==========
                    comment_text = random.choice(engagement_comments)
                    
                    # Click comment button first
                    comment_btn_selectors = [
                        "[aria-label='Leave a comment']",
                        "[aria-label='Comment']",
                        "div[aria-label*='Comment']",
                        "[aria-label*='comment']"
                    ]
                    
                    comment_btn_clicked = False
                    for btn_sel in comment_btn_selectors:
                        try:
                            comment_btn = post.find_element(By.CSS_SELECTOR, btn_sel)
                            comment_btn.click()
                            comment_btn_clicked = True
                            time.sleep(1)
                            break
                        except:
                            continue
                    
                    if comment_btn_clicked:
                        # Find comment input field
                        comment_input_selectors = [
                            "div[contenteditable='true'][role='textbox']",
                            "[aria-label='Write a comment']",
                            "[aria-label='Write a comment…']",
                            "[placeholder*='Write a comment']",
                            "div[data-lexical-editor='true']"
                        ]
                        
                        for input_sel in comment_input_selectors:
                            try:
                                comment_input = WebDriverWait(self.driver, 3).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, input_sel))
                                )
                                comment_input.click()
                                time.sleep(0.3)
                                comment_input.send_keys(comment_text)
                                time.sleep(0.5)
                                comment_input.send_keys(Keys.RETURN)
                                results["posts_commented"] += 1
                                post_log["actions"].append(f"commented: {comment_text[:30]}...")
                                print(f"[ENGAGE] Post {i}: Commented ✓")
                                time.sleep(1)
                                break
                            except:
                                continue
                    
                    results["engagement_log"].append(post_log)
                    
                    # Small delay between posts
                    time.sleep(random.uniform(1.5, 3.0))
                    
                except Exception as e:
                    post_log["error"] = str(e)
                    results["engagement_log"].append(post_log)
                    results["errors"].append(f"Post {i}: {str(e)}")
                    continue
            
            print(f"[ENGAGE] Complete! Liked: {results['posts_liked']}, Commented: {results['posts_commented']}, Followed: {results['users_followed']}")
            return results
            
        except Exception as e:
            results["success"] = False
            results["errors"].append(str(e))
            return results
    
    def quick_engage_scroll(self, scroll_and_engage_times: int = 10) -> dict:
        """
        Quick engagement: scroll down, engage with visible posts, repeat.
        Perfect for continuous group engagement.
        Automatically handles browser session recovery.
        """
        import random
        
        def ensure_browser_ready():
            """Helper to ensure browser is open and session is valid"""
            # Check if driver exists and session is valid
            if self.driver:
                try:
                    _ = self.driver.title  # Test if session is valid
                    return True
                except Exception as e:
                    print(f"[QUICK ENGAGE] Session invalid: {e}")
                    self.driver = None
            
            # Need to open browser
            print("[QUICK ENGAGE] Opening browser...")
            browser_result = self.open_browser()
            if not browser_result.get("success"):
                return False
            
            # Navigate to preferred Facebook group
            try:
                group_url = FACEBOOK_GROUPS.get("preferred", "https://www.facebook.com/groups/2080417442046498")
                print(f"[QUICK ENGAGE] Navigating to {group_url}")
                self.driver.get(group_url)
                time.sleep(4)
                return True
            except Exception as e:
                print(f"[QUICK ENGAGE] Navigation failed: {e}")
                return False
        
        # Ensure browser is ready
        if not ensure_browser_ready():
            return {"success": False, "error": "Failed to open browser or navigate to Facebook"}
        
        comments = [
            "🔥 #darrellbuttigieg #thesoldiersdream",
            "💪 Great! #darrellbuttigieg #thesoldiersdream",
            "👏 Nice! #darrellbuttigieg #thesoldiersdream",
            "⭐ Love it! #darrellbuttigieg #thesoldiersdream",
            "🙌 Awesome! #darrellbuttigieg #thesoldiersdream"
        ]
        
        results = {"liked": 0, "commented": 0, "scrolls": 0, "success": True}
        
        try:
            for cycle in range(scroll_and_engage_times):
                print(f"[QUICK ENGAGE] Cycle {cycle + 1}/{scroll_and_engage_times}")
                
                # Check session is still valid at each cycle
                try:
                    _ = self.driver.title
                except Exception as e:
                    print(f"[QUICK ENGAGE] Session lost during cycle {cycle}, recovering...")
                    if not ensure_browser_ready():
                        results["success"] = False
                        results["error"] = "Lost browser session and failed to recover"
                        return results
                
                # Find visible like buttons and click them
                try:
                    like_btns = self.driver.find_elements(By.CSS_SELECTOR, "[aria-label='Like']")
                    for btn in like_btns[:3]:  # Like up to 3 visible posts
                        try:
                            if btn.get_attribute("aria-pressed") != "true":
                                btn.click()
                                results["liked"] += 1
                                time.sleep(0.3)
                        except:
                            continue
                except:
                    pass
                
                # Comment on first visible post if possible
                try:
                    comment_btn = self.driver.find_element(By.CSS_SELECTOR, "[aria-label='Leave a comment'], [aria-label='Comment']")
                    comment_btn.click()
                    time.sleep(1)
                    
                    comment_input = self.driver.find_element(By.CSS_SELECTOR, "div[contenteditable='true'][role='textbox']")
                    comment_input.send_keys(random.choice(comments))
                    comment_input.send_keys(Keys.RETURN)
                    results["commented"] += 1
                    time.sleep(1)
                except:
                    pass
                
                # Scroll down
                self.driver.execute_script("window.scrollBy(0, 600);")
                results["scrolls"] += 1
                time.sleep(random.uniform(2, 4))
            
            return results
            
        except Exception as e:
            # One more recovery attempt
            error_str = str(e).lower()
            if "invalid session" in error_str or "no such window" in error_str:
                print("[QUICK ENGAGE] Final recovery attempt...")
                if ensure_browser_ready():
                    results["note"] = "Recovered from session error, partial results"
                    return results
            
            results["success"] = False
            results["error"] = str(e)
            return results
    
    # ═══════════════════════════════════════════════════════════════
    #           REPLY TO COMMENTS ENGAGEMENT TOOL
    # ═══════════════════════════════════════════════════════════════
    
    # Owner names to skip (never reply to your own comments)
    OWNER_NAMES = [
        "darrell buttigieg", "darrellbuttigieg", "darrell", "buttigieg",
        "amigos brenton", "amigosbrenton", "brenton", "agent amigos",
        "the soldier's dream", "thesoldiersdream", "soldier's dream"
    ]
    
    # Positive short replies to encourage follow back (50+ variations)
    POSITIVE_REPLIES = [
        # Fire/Energy
        "Love this! 🔥 Follow back?",
        "This is fire! 🔥 Let's connect!",
        "So good! 🔥 Following you!",
        "Straight fire! 🔥 Follow back?",
        # Agreement
        "So true! 💯 Let's connect!",
        "Facts! 💯 Follow back?",
        "100% agree! 💯 Following!",
        "Couldn't agree more! 💯",
        "This right here! 💯 Connect?",
        # Praise
        "Great point! 👏 Following you!",
        "Well said! 👏 Follow back?",
        "Perfectly put! 👏 Let's connect!",
        "Nailed it! 👏 Following!",
        "Brilliant! 👏 Follow back please!",
        # Positivity
        "This! 🙌 Follow for follow?",
        "Yes! 🙌 Let's support each other!",
        "Love it! 🙌 Following you now!",
        "Amazing! 🙌 Follow back?",
        # Support
        "Yes! 💪 Let's support each other!",
        "Let's grow together! 💪 Follow back?",
        "Supporting this! 💪 Following!",
        "Together we rise! 💪 Connect?",
        # Stars/Shine
        "Exactly! ⭐ Follow back please!",
        "You shine! ⭐ Following you!",
        "Star quality! ⭐ Let's connect!",
        "Brilliant! ✨ Follow back?",
        "This sparkles! ✨ Following!",
        # Connection
        "Well said! 🎯 Following!",
        "On point! 🎯 Let's connect!",
        "Spot on! 🎯 Follow back?",
        "Right on target! 🎯 Following!",
        # Quick positives
        "Nice! 👍 Let's grow together!",
        "Truth! 👍 Following you now!",
        "Agreed! 👍 Follow back?",
        "Right on! 👍 Let's connect!",
        # Gratitude
        "100%! 🙏 Follow back?",
        "Bless this! 🙏 Following!",
        "Grateful for this! 🙏 Connect?",
        "Thank you! 🙏 Follow back?",
        # Rainbow/Celebration
        "Absolutely! 🌟 Follow for follow!",
        "Yes yes! 🌟 Following!",
        "Incredible! 🌟 Let's connect!",
        "Wonderful! 🌈 Follow back?",
        # Heart
        "Love this so much! ❤️ Following!",
        "Heart this! ❤️ Follow back?",
        "Beautiful! ❤️ Let's connect!",
        # Short & Sweet
        "Yesss! 🙌 Follow?",
        "This! 💪 Following!",
        "Gold! ⭐ Connect?",
        "Real talk! 💯 Follow back?"
    ]
    
    def reply_to_post_comments(self, max_posts: int = 5) -> dict:
        """
        ENGAGEMENT TOOL: Find posts, open comments, like/follow commenters,
        and leave ONE positive reply per post (skipping own comments).
        
        Process:
        1. Find one post at a time
        2. Click on comments to expand
        3. Scroll through comments - like & follow each
        4. Leave ONE reply to a commenter (not yourself)
        5. Move to next post
        
        NOTE: Will try to attach to existing browser first (if Chrome is open with debugging).
        Start Chrome with: chrome.exe --remote-debugging-port=9222
        """
        import random
        
        results = {
            "success": True,
            "posts_processed": 0,
            "comments_liked": 0,
            "replies_sent": 0,
            "users_followed": 0,
            "skipped_own": 0,
            "engagement_log": [],
            "errors": []
        }
        
        # Smart browser detection - try to use existing browser first
        print("[REPLY ENGAGE] ════════════════════════════════")
        print("[REPLY ENGAGE] Checking for browser...")
        
        browser_result = self.ensure_browser_ready(require_facebook=True)
        if not browser_result.get("success"):
            return {"success": False, "error": f"Failed to get browser ready: {browser_result.get('error')}"}
        
        print(f"[REPLY ENGAGE] Browser ready via: {browser_result.get('method', 'unknown')}")
        print(f"[REPLY ENGAGE] Current URL: {browser_result.get('url', 'unknown')}")
        
        # Check if we're on a Facebook group/feed page
        current_url = self.driver.current_url
        if "facebook.com" not in current_url:
            print("[REPLY ENGAGE] Not on Facebook, navigating...")
            self.driver.get("https://www.facebook.com")
            time.sleep(3)
        
        try:
            print(f"[REPLY ENGAGE] Starting comment engagement on {max_posts} posts...")
            print(f"[REPLY ENGAGE] Will make ONE reply per post, skipping own comments")
            
            # Scroll to load some posts first
            for _ in range(3):
                self.driver.execute_script("window.scrollBy(0, 800);")
                time.sleep(1.5)
            
            # Scroll back to top
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            
            # Find all posts
            post_selectors = [
                "[role='feed'] [role='article']",
                "[data-pagelet^='FeedUnit']",
                "[data-pagelet^='GroupFeed'] [role='article']"
            ]
            
            posts = []
            for selector in post_selectors:
                try:
                    posts = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if posts:
                        print(f"[REPLY ENGAGE] Found {len(posts)} posts")
                        break
                except:
                    continue
            
            if not posts:
                return {"success": False, "error": "No posts found on page"}
            
            # Process each post one at a time
            for post_idx, post in enumerate(posts[:max_posts]):
                post_log = {
                    "post_index": post_idx,
                    "comments_liked": 0,
                    "replied": False,
                    "actions": []
                }
                
                try:
                    print(f"\n[REPLY ENGAGE] ═══ Post {post_idx + 1}/{min(len(posts), max_posts)} ═══")
                    
                    # Scroll post into view
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", post)
                    time.sleep(2)
                    
                    # ========== STEP 1: Click on Comments to expand ==========
                    comment_btn_selectors = [
                        "[aria-label='Leave a comment']",
                        "[aria-label='Comment']",
                        "div[aria-label*='Comment']",
                        "[aria-label*='comment']",
                        "//span[contains(text(), 'Comment')]"
                    ]
                    
                    comments_opened = False
                    for btn_sel in comment_btn_selectors:
                        try:
                            if btn_sel.startswith("//"):
                                comment_btn = post.find_element(By.XPATH, btn_sel)
                            else:
                                comment_btn = post.find_element(By.CSS_SELECTOR, btn_sel)
                            comment_btn.click()
                            comments_opened = True
                            print(f"  ✓ Opened comments")
                            post_log["actions"].append("opened_comments")
                            time.sleep(2)
                            break
                        except:
                            continue
                    
                    if not comments_opened:
                        print(f"  ✗ Could not open comments, skipping...")
                        post_log["actions"].append("comments_not_found")
                        results["engagement_log"].append(post_log)
                        continue
                    
                    # ========== STEP 2: Find all visible comments ==========
                    comment_selectors = [
                        "[aria-label*='Comment by']",
                        "div[role='article'] div[role='article']",
                        "ul[role='list'] > li"
                    ]
                    
                    comments = []
                    for com_sel in comment_selectors:
                        try:
                            comments = post.find_elements(By.CSS_SELECTOR, com_sel)
                            if comments:
                                break
                        except:
                            continue
                    
                    if not comments:
                        try:
                            comment_container = self.driver.find_element(By.CSS_SELECTOR, "[role='complementary'], [aria-label*='Comments']")
                            comments = comment_container.find_elements(By.CSS_SELECTOR, "div[role='article']")
                        except:
                            pass
                    
                    if not comments:
                        print(f"  ✗ No comments found")
                        post_log["actions"].append("no_comments")
                        results["engagement_log"].append(post_log)
                        continue
                    
                    print(f"  Found {len(comments)} comments")
                    
                    # ========== STEP 3: Process comments - Like all, Reply to ONE ==========
                    reply_made_for_this_post = False
                    
                    for comment_idx, comment in enumerate(comments[:10]):  # Max 10 comments per post
                        try:
                            # Scroll comment into view
                            try:
                                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", comment)
                                time.sleep(0.5)
                            except:
                                pass
                            
                            # Get commenter name to check if it's our own comment
                            commenter_name = ""
                            try:
                                name_el = comment.find_element(By.CSS_SELECTOR, "a[role='link'] span, strong, h3 span")
                                commenter_name = name_el.text.lower().strip()
                            except:
                                pass
                            
                            # Check if this is our own comment - SKIP IT
                            is_own_comment = any(owner in commenter_name for owner in self.OWNER_NAMES)
                            if is_own_comment:
                                print(f"  ⏭️ Skipping own comment by '{commenter_name[:20]}'")
                                results["skipped_own"] += 1
                                continue
                            
                            # ===== LIKE the comment =====
                            like_selectors = ["[aria-label='Like']", "[aria-label='like']", "span[aria-label*='Like']"]
                            for like_sel in like_selectors:
                                try:
                                    like_btn = comment.find_element(By.CSS_SELECTOR, like_sel)
                                    like_btn.click()
                                    results["comments_liked"] += 1
                                    post_log["comments_liked"] += 1
                                    time.sleep(0.3)
                                    break
                                except:
                                    continue
                            
                            # ===== FOLLOW the commenter =====
                            follow_selectors = ["[aria-label='Follow']", "[aria-label='follow']"]
                            for follow_sel in follow_selectors:
                                try:
                                    follow_btn = comment.find_element(By.CSS_SELECTOR, follow_sel)
                                    follow_btn.click()
                                    results["users_followed"] += 1
                                    time.sleep(0.3)
                                    break
                                except:
                                    continue
                            
                            # ===== REPLY - Only ONE per post =====
                            if not reply_made_for_this_post:
                                reply_selectors = ["[aria-label='Reply']", "[aria-label='reply']", "//span[text()='Reply']"]
                                
                                for reply_sel in reply_selectors:
                                    try:
                                        if reply_sel.startswith("//"):
                                            reply_btn = comment.find_element(By.XPATH, reply_sel)
                                        else:
                                            reply_btn = comment.find_element(By.CSS_SELECTOR, reply_sel)
                                        reply_btn.click()
                                        time.sleep(1)
                                        
                                        # Find reply input
                                        reply_input_selectors = [
                                            "div[contenteditable='true'][role='textbox']",
                                            "[aria-label='Write a reply']",
                                            "[aria-label='Write a reply…']"
                                        ]
                                        
                                        for input_sel in reply_input_selectors:
                                            try:
                                                reply_input = WebDriverWait(self.driver, 3).until(
                                                    EC.presence_of_element_located((By.CSS_SELECTOR, input_sel))
                                                )
                                                reply_input.click()
                                                time.sleep(0.3)
                                                
                                                # Type random positive reply
                                                reply_text = random.choice(self.POSITIVE_REPLIES)
                                                reply_input.send_keys(reply_text)
                                                time.sleep(0.5)
                                                reply_input.send_keys(Keys.RETURN)
                                                
                                                results["replies_sent"] += 1
                                                post_log["replied"] = True
                                                reply_made_for_this_post = True
                                                print(f"  💬 Replied: '{reply_text}'")
                                                time.sleep(1)
                                                break
                                            except:
                                                continue
                                        break
                                    except:
                                        continue
                            
                            time.sleep(random.uniform(0.5, 1.0))
                            
                        except Exception as e:
                            continue
                    
                    results["posts_processed"] += 1
                    results["engagement_log"].append(post_log)
                    
                    print(f"  ✅ Post {post_idx + 1} done: {post_log['comments_liked']} likes, replied={post_log['replied']}")
                    time.sleep(random.uniform(2.0, 3.5))
                    
                except Exception as e:
                    post_log["error"] = str(e)[:100]
                    results["engagement_log"].append(post_log)
                    results["errors"].append(f"Post {post_idx}: {str(e)[:100]}")
                    continue
            
            print(f"\n[REPLY ENGAGE] ════════════════════════════════")
            print(f"[REPLY ENGAGE] ✅ COMPLETE!")
            print(f"[REPLY ENGAGE] Posts: {results['posts_processed']}")
            print(f"[REPLY ENGAGE] Comments Liked: {results['comments_liked']}")
            print(f"[REPLY ENGAGE] Replies Sent: {results['replies_sent']}")
            print(f"[REPLY ENGAGE] Users Followed: {results['users_followed']}")
            print(f"[REPLY ENGAGE] Own Comments Skipped: {results['skipped_own']}")
            print(f"[REPLY ENGAGE] ════════════════════════════════")
            
            return results
            
        except Exception as e:
            results["success"] = False
            results["errors"].append(str(e))
            return results
    
    # ═══════════════════════════════════════════════════════════════
    #           SOCIAL MEDIA DATABASE TOOLS
    # ═══════════════════════════════════════════════════════════════
    
    def get_platform_info(self, platform: str) -> dict:
        """Get information about a social media platform from database"""
        try:
            platforms = SOCIAL_MEDIA_PLATFORMS.get("platforms", {})
            if platform.lower() in platforms:
                return {"success": True, "platform": platform, "info": platforms[platform.lower()]}
            return {"success": False, "error": f"Platform '{platform}' not found in database"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_all_platforms(self) -> dict:
        """List all available social media platforms"""
        try:
            platforms = SOCIAL_MEDIA_PLATFORMS.get("platforms", {})
            platform_list = []
            for key, info in platforms.items():
                platform_list.append({
                    "id": key,
                    "name": info.get("name", key),
                    "base_url": info.get("base_url", ""),
                    "char_limit": info.get("char_limit", "unknown")
                })
            return {"success": True, "count": len(platform_list), "platforms": platform_list}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def open_platform(self, platform: str, page: str = "feed") -> dict:
        """Open a social media platform by name"""
        try:
            platforms = SOCIAL_MEDIA_PLATFORMS.get("platforms", {})
            if platform.lower() not in platforms:
                return {"success": False, "error": f"Platform '{platform}' not found"}
            
            platform_info = platforms[platform.lower()]
            
            # Determine which URL to use based on page type
            url_key = f"{page}_url"
            if url_key in platform_info:
                url = platform_info[url_key]
            elif "base_url" in platform_info:
                url = platform_info["base_url"]
            else:
                return {"success": False, "error": f"No URL found for {platform}"}
            
            result = self.open_url_default_browser(url)
            if result.get("success"):
                return {"success": True, "platform": platform, "page": page, "url": url}
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_quick_post_url(self, platform: str) -> dict:
        """Get the direct posting URL for a platform"""
        try:
            quick_links = SOCIAL_MEDIA_PLATFORMS.get("quick_links", {})
            key = f"post_{platform.lower()}"
            if key in quick_links:
                return {"success": True, "platform": platform, "url": quick_links[key]}
            
            # Fallback to platforms database
            platforms = SOCIAL_MEDIA_PLATFORMS.get("platforms", {})
            if platform.lower() in platforms:
                info = platforms[platform.lower()]
                url = info.get("create_post_url") or info.get("upload_url") or info.get("new_post_url") or info.get("base_url")
                return {"success": True, "platform": platform, "url": url}
            
            return {"success": False, "error": f"No post URL found for {platform}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def open_platform_to_post(self, platform: str) -> dict:
        """Open a platform directly to the post/create page"""
        try:
            url_result = self.get_quick_post_url(platform)
            if not url_result.get("success"):
                return url_result
            
            result = self.open_url_default_browser(url_result["url"])
            if result.get("success"):
                return {"success": True, "platform": platform, "url": url_result["url"], "action": "ready_to_post"}
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_trending_hashtags(self, category: str = "general") -> dict:
        """Get trending hashtags by category"""
        try:
            hashtags = SOCIAL_MEDIA_PLATFORMS.get("trending_hashtags", {})
            if category.lower() in hashtags:
                tags = hashtags[category.lower()]
                # Always include owner hashtags
                owner_tags = hashtags.get("owner", [])
                return {"success": True, "category": category, "hashtags": tags, "owner_hashtags": owner_tags}
            return {"success": False, "error": f"Category '{category}' not found", "available": list(hashtags.keys())}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_engagement_phrases(self, phrase_type: str = "comments") -> dict:
        """Get engagement phrases for social media interactions"""
        try:
            phrases = SOCIAL_MEDIA_PLATFORMS.get("engagement_phrases", {})
            if phrase_type.lower() in phrases:
                return {"success": True, "type": phrase_type, "phrases": phrases[phrase_type.lower()]}
            return {"success": False, "error": f"Phrase type '{phrase_type}' not found", "available": list(phrases.keys())}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_platform_limits(self, platform: str) -> dict:
        """Get character limits and recommendations for a platform"""
        try:
            platforms = SOCIAL_MEDIA_PLATFORMS.get("platforms", {})
            if platform.lower() not in platforms:
                return {"success": False, "error": f"Platform '{platform}' not found"}
            
            info = platforms[platform.lower()]
            limits = {
                "char_limit": info.get("char_limit"),
                "optimal_length": info.get("optimal_post_length") or info.get("optimal_title_length"),
                "hashtag_limit": info.get("hashtag_limit"),
                "recommended_hashtags": info.get("recommended_hashtags"),
                "best_posting_times": info.get("best_posting_times"),
                "video_formats": info.get("video_formats"),
                "image_formats": info.get("image_formats"),
                "max_video_length": info.get("max_video_length_seconds")
            }
            return {"success": True, "platform": platform, "limits": limits}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_facebook_groups(self) -> dict:
        """Get saved Facebook groups from database"""
        try:
            groups = SOCIAL_MEDIA_PLATFORMS.get("facebook_groups", {})
            return {"success": True, "count": len(groups), "groups": groups}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def open_all_platforms(self) -> dict:
        """Open all major social media platforms in tabs"""
        try:
            platforms_to_open = ["facebook", "instagram", "twitter", "linkedin", "tiktok", "youtube"]
            opened = []
            
            for p in platforms_to_open:
                result = self.open_platform(p, "feed")
                if result.get("success"):
                    opened.append(p)
                time.sleep(0.5)
            
            return {"success": True, "opened": opened, "count": len(opened)}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Singleton instance
web = WebTools()
