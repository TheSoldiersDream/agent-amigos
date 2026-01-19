"""Core scraping utilities for Agent Amigos.

Provides static HTTP fetching with optional BeautifulSoup parsing,
selector-based extraction, batch scraping, and lightweight change
monitoring stored on disk. Designed to keep dependencies minimal while
remaining resilient to slow or flaky sites.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import requests

try:  # Optional dependency loaded lazily
    from bs4 import BeautifulSoup

    BS4_AVAILABLE = True
except ImportError:  # pragma: no cover - handled at runtime
    BeautifulSoup = None
    BS4_AVAILABLE = False

logger = logging.getLogger(__name__)

DATA_ROOT = Path(__file__).resolve().parents[2] / "data" / "scraper"
DATA_ROOT.mkdir(parents=True, exist_ok=True)
MONITOR_DIR = DATA_ROOT / "monitors"
MONITOR_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR = DATA_ROOT / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_HEADERS = {
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "accept-language": "en-US,en;q=0.9",
}


@dataclass
class ScrapeResult:
    url: str
    status_code: Optional[int]
    success: bool
    elapsed: float
    content_length: Optional[int] = None
    text: Optional[str] = None
    html: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    links: Optional[List[Dict[str, str]]] = None
    matches: Optional[Dict[str, List[str]]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "url": self.url,
            "status_code": self.status_code,
            "success": self.success,
            "elapsed": round(self.elapsed, 3),
            "content_length": self.content_length,
        }
        if self.text is not None:
            payload["text"] = self.text
        if self.html is not None:
            payload["html"] = self.html
        if self.metadata:
            payload["metadata"] = self.metadata
        if self.links is not None:
            payload["links"] = self.links
        if self.matches is not None:
            payload["matches"] = self.matches
        if self.error:
            payload["error"] = self.error
        return payload


class ScraperEngine:
    """High-level interface for static scraping tasks."""

    def __init__(self, max_workers: int = 4):
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.max_workers = max_workers

    @staticmethod
    def _ensure_bs4() -> None:
        if not BS4_AVAILABLE or BeautifulSoup is None:
            raise RuntimeError(
                "BeautifulSoup not installed. Run: pip install beautifulsoup4 lxml"
            )

    def _build_metadata(self, soup: "BeautifulSoup") -> Dict[str, Any]:
        metadata: Dict[str, Any] = {}
        title = soup.title.string.strip() if soup.title and soup.title.string else None
        if title:
            metadata["title"] = title
        description = soup.find("meta", attrs={"name": "description"})
        if description and description.get("content"):
            metadata["description"] = description.get("content").strip()
        keywords = soup.find("meta", attrs={"name": "keywords"})
        if keywords and keywords.get("content"):
            metadata["keywords"] = [
                token.strip()
                for token in keywords.get("content").split(",")
                if token.strip()
            ]
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            metadata["og:title"] = og_title.get("content")
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            metadata["og:description"] = og_desc.get("content")
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            metadata["og:image"] = og_image.get("content")
        return metadata

    def _collect_links(self, soup: "BeautifulSoup", max_links: int) -> List[Dict[str, str]]:
        links: List[Dict[str, str]] = []
        for tag in soup.find_all("a", href=True)[:max_links]:
            text = tag.get_text(strip=True)
            links.append({"href": tag["href"], "text": text})
        return links

    def _collect_matches(
        self, soup: "BeautifulSoup", selectors: Iterable[str], include_html: bool
    ) -> Dict[str, List[str]]:
        matches: Dict[str, List[str]] = {}
        for selector in selectors:
            try:
                nodes = soup.select(selector)
            except Exception as exc:  # pragma: no cover - bs4 handles selectors
                matches[selector] = [f"Selector error: {exc}"]
                continue
            bucket: List[str] = []
            for node in nodes:
                bucket.append(node.decode() if include_html else node.get_text(strip=True))
            matches[selector] = bucket
        return matches

    def scrape_url(
        self,
        url: str,
        selectors: Optional[Iterable[str]] = None,
        include_text: bool = True,
        include_html: bool = False,
        include_links: bool = False,
        max_links: int = 50,
        timeout: int = 20,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        start = time.perf_counter()
        response = None
        try:
            request_headers = {**DEFAULT_HEADERS, **(headers or {})}
            response = self.session.get(
                url,
                headers=request_headers,
                timeout=timeout,
            )
            response.raise_for_status()
            html = response.text
            text_content: Optional[str] = html if include_text else None
            matches = None
            metadata = None
            links = None

            if selectors or include_links or include_text or include_html:
                self._ensure_bs4()
                soup = BeautifulSoup(html, "lxml") if BeautifulSoup else None
                if soup:
                    if include_text and text_content is not None:
                        text_content = soup.get_text(" ", strip=True)
                    if selectors:
                        matches = self._collect_matches(
                            soup, selectors, include_html=include_html
                        )
                    if include_links:
                        links = self._collect_links(soup, max_links=max_links)
                    metadata = self._build_metadata(soup)

            result = ScrapeResult(
                url=url,
                status_code=response.status_code,
                success=True,
                elapsed=time.perf_counter() - start,
                content_length=len(response.content) if response else None,
                text=text_content,
                html=response.text if include_html else None,
                metadata=metadata,
                links=links,
                matches=matches,
            )
            return result.to_dict()
        except Exception as exc:
            logger.warning("Scrape failed for %s: %s", url, exc)
            status_code = getattr(response, "status_code", None)
            err = ScrapeResult(
                url=url,
                status_code=status_code,
                success=False,
                elapsed=time.perf_counter() - start,
                error=str(exc),
            )
            return err.to_dict()

    def scrape_multiple(
        self,
        urls: Iterable[str],
        selectors: Optional[Iterable[str]] = None,
        include_text: bool = True,
        include_links: bool = False,
        include_html: bool = False,
        timeout: int = 20,
    ) -> Dict[str, Any]:
        urls_list = list(urls)
        results: Dict[str, Any] = {"success": True, "results": []}
        if not urls_list:
            return {"success": False, "error": "No URLs provided", "results": []}

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_map = {
                executor.submit(
                    self.scrape_url,
                    url,
                    selectors=selectors,
                    include_text=include_text,
                    include_links=include_links,
                    include_html=include_html,
                    timeout=timeout,
                ): url
                for url in urls_list
            }
            for future in as_completed(future_map):
                results["results"].append(future.result())
        return results

    def _monitor_file(self, url: str) -> Path:
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return MONITOR_DIR / f"{key}.json"

    def monitor_webpage(
        self,
        url: str,
        selectors: Optional[Iterable[str]] = None,
        include_html: bool = False,
        include_links: bool = False,
    ) -> Dict[str, Any]:
        current = self.scrape_url(
            url,
            selectors=selectors,
            include_text=True,
            include_links=include_links,
            include_html=include_html,
        )
        if not current.get("success"):
            return current

        text_blob = json.dumps(current.get("matches") or current.get("text") or "")
        signature = hashlib.sha256(text_blob.encode("utf-8")).hexdigest()
        record = {
            "timestamp": time.time(),
            "signature": signature,
            "payload": current,
        }
        file_path = self._monitor_file(url)

        previous = None
        if file_path.exists():
            try:
                previous = json.loads(file_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                previous = None

        file_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        changed = previous is None or previous.get("signature") != signature
        delta = {
            "success": True,
            "url": url,
            "changed": changed,
            "current_signature": signature,
            "previous_signature": previous.get("signature") if previous else None,
            "last_checked": record["timestamp"],
        }
        if changed:
            delta["payload"] = current
        return delta


scraper_engine = ScraperEngine()
