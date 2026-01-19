"""Simple marketplace search helpers.

This module provides a lightweight `search_products` function that performs a web_search,
fetches candidate pages, extracts a best-effort price and currency, and returns normalized
results including converted AUD and PHP prices using `currency.convert`.

This is intentionally conservative (no purchases), and focuses on discoverability only.
"""
from __future__ import annotations

import re
import time
import logging
from typing import List, Dict, Optional, Iterable, Tuple

from .currency import convert
from .web_tools import web
from .scraper_tools import scrape_url, scrape_dynamic

logger = logging.getLogger(__name__)

PRICE_RE = re.compile(
    r"(?P<currency>US\$|AUD\$|AUD|PHP|Php|₱|\$|P)\s*(?P<price>[0-9][0-9\.,]*)",
    re.IGNORECASE,
)
SYMBOL_TO_CUR = {
    "$": "AUD",
    "AUD$": "AUD",
    "AUD": "AUD",
    "US$": "USD",
    "₱": "PHP",
    "PHP": "PHP",
    "PHP": "PHP",
    "Php": "PHP",
    "P": "PHP",
}


_CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


def _looks_non_english(text: str) -> bool:
    if not text:
        return False
    return bool(_CJK_RE.search(text))


def _iter_search_queries(query: str, region: str) -> Iterable[str]:
    q = (query or "").strip()
    if not q:
        return []

    region_u = (region or "").upper().strip()
    # Always start with the raw query.
    queries = [q]

    if region_u == "PH":
        # Force English + local intent.
        queries.extend(
            [
                f"{q} price Philippines PHP",
                f"{q} site:lazada.com.ph",
                f"{q} site:shopee.ph",
                "Starlink Philippines kit price site:starlink.com",
            ]
        )
    elif region_u == "AU":
        queries.extend([f"{q} price Australia AUD", f"{q} site:starlink.com", f"{q} site:amazon.com.au"])
    else:
        queries.extend([f"{q} price", f"{q} site:starlink.com"])

    # De-dupe, preserve order.
    seen = set()
    out: List[str] = []
    for item in queries:
        item_n = re.sub(r"\s+", " ", item).strip()
        if item_n and item_n.lower() not in seen:
            seen.add(item_n.lower())
            out.append(item_n)
    return out


def _parse_price_from_html(html: str) -> Optional[Dict[str, object]]:
    if not html:
        return None

    # JSON-LD / structured data patterns.
    cur_m = re.search(r"\"priceCurrency\"\s*:\s*\"(?P<cur>[A-Z]{3})\"", html)
    price_m = re.search(r"\"price\"\s*:\s*\"?(?P<price>[0-9][0-9\.,]*)\"?", html)
    if cur_m and price_m:
        cur = cur_m.group("cur").upper()
        raw = price_m.group("price").replace(",", "")
        try:
            return {"amount": float(raw), "currency": cur}
        except Exception:
            return None

    # OpenGraph / meta tags.
    m_amount = re.search(r"product:price:amount\"\s+content=\"(?P<price>[0-9][0-9\.,]*)\"", html, re.I)
    m_cur = re.search(r"product:price:currency\"\s+content=\"(?P<cur>[A-Z]{3})\"", html, re.I)
    if m_amount and m_cur:
        cur = m_cur.group("cur").upper()
        raw = m_amount.group("price").replace(",", "")
        try:
            return {"amount": float(raw), "currency": cur}
        except Exception:
            return None

    return None


def _parse_price(text: str) -> Optional[Dict[str, object]]:
    if not text:
        return None
    m = PRICE_RE.search(text)
    if not m:
        # Try currency codes inline
        m2 = re.search(r"(?P<price>[0-9][0-9\.,]{1,})\s*(?P<code>AUD|PHP|USD|SGD|EUR)", text, re.I)
        if m2:
            price = m2.group("price").replace(",", "")
            cur = (m2.group("code") or "AUD").upper()
            try:
                return {"amount": float(price), "currency": cur}
            except Exception:
                return None
        return None

    sym = (m.group("currency") or "").strip()
    price = (m.group("price") or "").replace(",", "")
    sym_norm = sym.upper().replace(" ", "")
    cur = SYMBOL_TO_CUR.get(sym_norm) or SYMBOL_TO_CUR.get(sym) or "AUD"
    try:
        return {"amount": float(price), "currency": cur}
    except Exception:
        return None


def search_products(
    query: str,
    region: str = "PH",
    currencies: Optional[List[str]] = None,
    limit: int = 8,
    dynamic_fallback: bool = True,
) -> Dict[str, object]:
    """Search marketplaces and return normalized product list.

    Returns:
      {"query": str, "results": [{title, url, seller, price:{amount,currency}, price_aud, price_php, snippet}], "meta": {}}
    """
    currencies = currencies or ["AUD", "PHP"]
    max_results = min(10, max(5, limit * 2))

    # Run multiple region-focused queries and merge hits.
    merged_hits: List[Dict[str, object]] = []
    seen_urls = set()
    for q in _iter_search_queries(query, region):
        resp = web.web_search(q, max_results=max_results)
        hits = resp.get("results", []) if isinstance(resp, dict) else []
        for h in hits:
            if not isinstance(h, dict):
                continue
            url = h.get("href") or h.get("url") or h.get("link")
            if not url or not isinstance(url, str):
                continue
            if url in seen_urls:
                continue
            seen_urls.add(url)
            merged_hits.append(h)

    hits = merged_hits

    out: List[Dict[str, object]] = []
    # If we have at least a few English-ish hits, prefer them.
    englishish = [h for h in hits if not _looks_non_english(str(h.get("title") or ""))]
    candidate_hits = englishish if len(englishish) >= min(3, len(hits)) else hits

    for h in candidate_hits[: limit * 3]:
        url = h.get("href") or h.get("url") or h.get("link")
        if not isinstance(url, str) or not url:
            continue
        title = str(h.get("title") or "")
        snippet = str(h.get("body") or "")
        try:
            scraped = scrape_url(url, include_text=True, include_html=False, include_links=False, timeout=10)
        except Exception as e:
            logger.debug("scrape failed for %s: %s", url, e)
            scraped = {}

        text = str((scraped.get("text") or "")[:8000] or snippet or title)
        price = _parse_price(text) or _parse_price(title) or _parse_price(snippet)

        # Marketplace pages (Shopee/Lazada/etc.) are often JS-rendered; try a dynamic scrape
        # only if we didn't find a price via static text/snippet.
        if dynamic_fallback and not price:
            try:
                dyn = scrape_dynamic(
                    url,
                    wait_timeout=8.0,
                    headless=True,
                    locale="en-US",
                    extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
                )
                dyn_text = (dyn.get("text") or "")[:12000]
                dyn_html = dyn.get("html") or ""
                price = (
                    _parse_price(dyn_text)
                    or _parse_price_from_html(str(dyn_html))
                    or price
                )
            except Exception as e:
                logger.debug("dynamic scrape failed for %s: %s", url, e)

        seller = None
        meta = scraped.get("metadata") if isinstance(scraped, dict) else None
        if isinstance(meta, dict):
            seller = meta.get("title")

        item = {
            "title": title,
            "url": url,
            "seller": seller,
            "snippet": snippet,
            "price": price,
            "price_converted": {},
        }

        if price and price.get("amount") is not None:
            try:
                amt = float(price["amount"])  # type: ignore[arg-type]
            except Exception:
                amt = None
            frm = str(price.get("currency") or "AUD")
            for target in currencies:
                if amt is None:
                    break
                conv = convert(amt, frm, str(target))
                if conv is not None:
                    item["price_converted"][target] = conv
        out.append(item)
        if len(out) >= limit:
            break

    return {"query": query, "region": region, "results": out, "meta": {"hits": len(hits)}}