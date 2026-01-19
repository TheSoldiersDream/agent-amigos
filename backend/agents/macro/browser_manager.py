import asyncio
import logging
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = logging.getLogger(__name__)

class BrowserManager:
    """
    Manages Playwright browser instances for the Autonomous Macro Agent.
    """
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
    async def start(self):
        """Start the browser instance"""
        if self.browser:
            return
            
        logger.info(f"Starting Playwright browser (headless={self.headless})...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        self.page = await self.context.new_page()
        logger.info("✓ Browser started and page initialized")
        
    async def stop(self):
        """Stop the browser instance"""
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
        logger.info("Browser stopped")
        
    async def navigate(self, url: str):
        """Navigate to a URL"""
        if not self.page:
            await self.start()
        
        logger.info(f"Navigating to: {url}")
        await self.page.goto(url, wait_until="networkidle")
        
    async def get_page_state(self) -> Dict[str, Any]:
        """Get the current page state for perception"""
        if not self.page:
            return {}
            
        # Get screenshot as base64 or bytes? Let's do bytes for internal use
        screenshot = await self.page.screenshot()
        
        # Get basic DOM info
        title = await self.page.title()
        url = self.page.url
        
        return {
            "title": title,
            "url": url,
            "screenshot_bytes": screenshot,
            "viewport": self.page.viewport_size
        }
        
    async def click(self, selector: str):
        """Click an element"""
        if self.page:
            await self.page.click(selector)
            
    async def fill(self, selector: str, value: str):
        """Fill an input field"""
        if self.page:
            await self.page.fill(selector, value)
            
    async def type(self, selector: str, value: str, delay: int = 100):
        """Type into an input field with delay"""
        if self.page:
            await self.page.type(selector, value, delay=delay)
