"""Playwright-powered dynamic scraping helper."""
from __future__ import annotations

import asyncio
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

# Ensure subprocess support on Windows for Playwright
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

if TYPE_CHECKING:  # pragma: no cover
    from playwright.async_api import ViewportSize

try:  # Optional heavy dependency
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
    try:
        from playwright_stealth import stealth_async
        STEALTH_AVAILABLE = True
    except ImportError:
        STEALTH_AVAILABLE = False

    PLAYWRIGHT_AVAILABLE = True
except ImportError:  # pragma: no cover - optional
    async_playwright = None
    PlaywrightTimeout = Exception
    PLAYWRIGHT_AVAILABLE = False

from agent_mcp.automation.browser_actions import BrowserActionExecutor

logger = logging.getLogger(__name__)

# Global semaphore to prevent memory exhaustion from too many concurrent browsers
# Limits the number of Chromium instances running simultaneously across the app.
MAX_CONCURRENT_BROWSERS = 3
_browser_semaphore = asyncio.Semaphore(MAX_CONCURRENT_BROWSERS)

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "media_outputs" / "images"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _run_blocking(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    new_loop = asyncio.new_event_loop()
    try:
        return new_loop.run_until_complete(coro)
    finally:
        new_loop.close()


class DynamicScraper:
    """Wraps Playwright for one-off page renders and targeted extraction."""

    def __init__(self) -> None:
        self.action_executor = BrowserActionExecutor()

    async def _scrape_async(
        self,
        url: str,
        wait_for_selector: Optional[str] = None,
        wait_timeout: float = 10.0,
        actions: Optional[List[Dict[str, Any]]] = None,
        headless: bool = True,
        viewport: Optional["ViewportSize"] = None,
        screenshot: bool = False,
        proxy: Optional[Dict[str, Any]] = None,
        locale: Optional[str] = "en-US",
        extra_http_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        if not PLAYWRIGHT_AVAILABLE or async_playwright is None:
            raise RuntimeError(
                "Playwright not installed. Run: pip install playwright && playwright install chromium"
            )

        async with _browser_semaphore:
            logger.info("Starting dynamic scrape for %s (headless=%s) [Semaphore Slot Acquired]", url, headless)
            async with async_playwright() as p:
                # Support optional Playwright proxy settings (e.g., {'server': 'http://host:port', 'username': 'u', 'password': 'p'})
                launch_kwargs = {'headless': headless}
                if proxy:
                    launch_kwargs['proxy'] = proxy
                
                try:
                    browser = await p.chromium.launch(**launch_kwargs)
                except Exception as e:
                    logger.error("Failed to launch chromium: %s", e)
                    raise

                try:
                    # Create a locale-aware browser context with English defaults unless overridden.
                    context_kwargs = {}
                    if locale:
                        context_kwargs['locale'] = locale
                    # Merge Accept-Language header with any caller-provided headers.
                    default_al = f"{(locale or 'en-US')},en;q=0.9"
                    headers = {'Accept-Language': default_al}
                    if extra_http_headers:
                        headers.update(extra_http_headers)
                    context_kwargs['extra_http_headers'] = headers

                    context = await browser.new_context(**context_kwargs)
                    page = await context.new_page()

                    if STEALTH_AVAILABLE:
                        await stealth_async(page)

                    if viewport:
                        # Playwright expects a ViewportSize TypedDict: {"width": int, "height": int}
                        # Some callers may pass extra keys; keep only what Playwright needs.
                        viewport_size: ViewportSize = {
                            "width": int(viewport["width"]),
                            "height": int(viewport["height"]),
                        }
                        await page.set_viewport_size(viewport_size)

                    logger.info("Dynamic scrape navigating to %s", url)
                    try:
                        # Try networkidle first for data-heavy sites (like betting sites)
                        await page.goto(url, wait_until="networkidle", timeout=int(wait_timeout * 1000))
                    except Exception as e:
                        logger.warning("Networkidle wait failed for %s, falling back to domcontentloaded: %s", url, e)
                        try:
                            await page.goto(url, wait_until="domcontentloaded", timeout=int(wait_timeout * 1000))
                            # Give extra time for React/SPA to render after basic DOM is ready
                            await asyncio.sleep(3.0)
                        except Exception as e2:
                            logger.warning("Final navigation wait failed for %s: %s", url, e2)

                    if wait_for_selector:
                        try:
                            await page.wait_for_selector(wait_for_selector, state="attached", timeout=int(wait_timeout * 1000))
                        except PlaywrightTimeout as exc:
                            logger.warning("Timeout waiting for %s on %s: %s", wait_for_selector, url, exc)

                    action_log: List[Dict[str, Any]] = []
                    if actions:
                        action_log = await self.action_executor.run(page, actions)

                    html = await page.content()
                    # Try to get inner text of body. Fallback to whole content if body is suspicious.
                    try:
                        text = await page.inner_text("body")
                    except Exception:
                        text = ""
                    
                    if not text or len(text) < 10:
                        # Might be JSON wrapped in pre
                        try:
                            text = await page.inner_text("pre")
                        except Exception:
                            pass

                    screenshot_path = None
                    if screenshot:
                        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                        screenshot_path = OUTPUT_DIR / f"dynamic_{timestamp}.png"
                        await page.screenshot(path=str(screenshot_path), full_page=True)

                finally:
                    # Cleanly close context and browser
                    try:
                        await browser.close()
                    except Exception:
                        pass
                    logger.info("Finished dynamic scrape for %s", url)

        return {
            "success": True,
            "url": url,
            "html": html,
            "text": text,
            "actions": action_log,
            "screenshot": str(screenshot_path) if screenshot_path else None,
        }

    async def scrape(self, **kwargs: Any) -> Dict[str, Any]:
        return await self._scrape_async(**kwargs)

    def scrape_sync(self, **kwargs: Any) -> Dict[str, Any]:
        return _run_blocking(self._scrape_async(**kwargs))


dynamic_scraper = DynamicScraper()
