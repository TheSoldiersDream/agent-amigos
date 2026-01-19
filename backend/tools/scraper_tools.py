"""High-level tool wrappers around scraper modules."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from agent_mcp.scraper.ai_extractor import aiextractor
from agent_mcp.scraper.dynamic_scraper import dynamic_scraper
from agent_mcp.scraper.scraper_engine import scraper_engine


def scrape_url(
    url: str,
    selectors: Optional[List[str]] = None,
    include_text: bool = True,
    include_links: bool = False,
    include_html: bool = False,
    max_links: int = 50,
    timeout: int = 20,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    return scraper_engine.scrape_url(
        url=url,
        selectors=selectors,
        include_text=include_text,
        include_links=include_links,
        include_html=include_html,
        max_links=max_links,
        timeout=timeout,
        headers=headers,
    )


def scrape_batch(
    urls: Iterable[str],
    selectors: Optional[List[str]] = None,
    include_text: bool = True,
    include_links: bool = False,
    include_html: bool = False,
    timeout: int = 20,
) -> Dict[str, Any]:
    return scraper_engine.scrape_multiple(
        urls=urls,
        selectors=selectors,
        include_text=include_text,
        include_links=include_links,
        include_html=include_html,
        timeout=timeout,
    )


def monitor_webpage(
    url: str,
    selectors: Optional[List[str]] = None,
    include_html: bool = False,
    include_links: bool = False,
) -> Dict[str, Any]:
    return scraper_engine.monitor_webpage(
        url=url,
        selectors=selectors,
        include_html=include_html,
        include_links=include_links,
    )


def scrape_dynamic(
    url: str,
    wait_for_selector: Optional[str] = None,
    wait_timeout: float = 10.0,
    actions: Optional[List[Dict[str, Any]]] = None,
    headless: bool = True,
    viewport: Optional[Dict[str, int]] = None,
    screenshot: bool = False,
    proxy: Optional[Dict[str, Any]] = None,
    locale: Optional[str] = "en-US",
    extra_http_headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Proxy can be passed as Playwright proxy dict: {'server': 'http://host:port', 'username': 'u', 'password': 'p'}"""
    return dynamic_scraper.scrape_sync(
        url=url,
        wait_for_selector=wait_for_selector,
        wait_timeout=wait_timeout,
        actions=actions,
        headless=headless,
        viewport=viewport,
        screenshot=screenshot,
        proxy=proxy,
        locale=locale,
        extra_http_headers=extra_http_headers,
    )


def summarize_content(
    content: str,
    instructions: Optional[str] = None,
    max_words: int = 200,
) -> Dict[str, Any]:
    return aiextractor.summarize(
        content=content,
        instructions=instructions,
        max_words=max_words,
    )


def extract_data(
    content: str,
    schema_description: str,
) -> Dict[str, Any]:
    result = aiextractor.extract_structured(
        content=content,
        schema_description=schema_description,
    )
    if result.get("success") and result.get("extracted"):
        import json
        import re
        try:
            # Clean up potential markdown blocks
            message = result.get("extracted", "")
            json_match = re.search(r"(\{.*\})", message, re.DOTALL)
            if json_match:
                message = json_match.group(1)
            return json.loads(message)
        except Exception:
            return result
    return result


def ask_ai(
    question: str,
    context: Optional[str] = None,
) -> Dict[str, Any]:
    return aiextractor.ask(
        question=question,
        context=context,
    )
