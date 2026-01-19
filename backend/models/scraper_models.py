"""Pydantic schemas for scraper endpoints."""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, HttpUrl, conint


class ScrapeRequest(BaseModel):
    url: HttpUrl
    selectors: Optional[List[str]] = None
    include_text: bool = True
    include_links: bool = False
    include_html: bool = False
    max_links: conint(ge=1, le=200) = 50  # type: ignore[valid-type]
    headers: Optional[Dict[str, str]] = None
    timeout: conint(ge=5, le=60) = 20  # type: ignore[valid-type]


class BatchScrapeRequest(BaseModel):
    urls: List[HttpUrl]
    selectors: Optional[List[str]] = None
    include_text: bool = True
    include_links: bool = False
    include_html: bool = False
    timeout: conint(ge=5, le=60) = 20  # type: ignore[valid-type]


class DynamicAction(BaseModel):
    type: str
    selector: Optional[str] = None
    value: Optional[str] = None
    timeout: Optional[int] = 10000
    seconds: Optional[float] = None
    amount: Optional[int] = None
    press_enter: Optional[bool] = False
    path: Optional[str] = None


class DynamicScrapeRequest(BaseModel):
    url: HttpUrl
    wait_for_selector: Optional[str] = None
    wait_timeout: float = 10.0
    actions: Optional[List[DynamicAction]] = None
    headless: bool = True
    viewport: Optional[Dict[str, int]] = None
    screenshot: bool = False


class AISummaryRequest(BaseModel):
    content: str
    instructions: Optional[str] = None
    max_words: conint(ge=50, le=800) = 200  # type: ignore[valid-type]


class MonitorRequest(BaseModel):
    url: HttpUrl
    selectors: Optional[List[str]] = None
    include_html: bool = False
    include_links: bool = False
