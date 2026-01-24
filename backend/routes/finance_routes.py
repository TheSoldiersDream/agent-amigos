"""Finance data aggregation routes (crypto intel + movers).

Uses public market data sources (CoinGecko) to surface:
- trending coins
- fast movers (24h gainers)
- emerging small-cap list

This is informational only (not financial advice).
"""

from __future__ import annotations

from fastapi import APIRouter
from typing import Any, Dict, List, Optional, Tuple
import time
import requests

router = APIRouter(prefix="/finance", tags=["finance"])

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
DEFAULT_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "AgentAmigos/finance-intel",
}

_CACHE: Dict[str, Tuple[float, Any]] = {}


def _cache_get(key: str, ttl_seconds: int) -> Optional[Any]:
    item = _CACHE.get(key)
    if not item:
        return None
    ts, data = item
    if (time.time() - ts) > ttl_seconds:
        return None
    return data


def _cache_set(key: str, data: Any) -> None:
    _CACHE[key] = (time.time(), data)


def _safe_float(val: Any) -> Optional[float]:
    try:
        return float(val)
    except Exception:
        return None


def _fetch_markets(order: str, per_page: int) -> List[Dict[str, Any]]:
    resp = requests.get(
        f"{COINGECKO_BASE}/coins/markets",
        params={
            "vs_currency": "aud",
            "order": order,
            "per_page": per_page,
            "page": 1,
            "sparkline": "false",
            "price_change_percentage": "1h,24h,7d",
        },
        headers=DEFAULT_HEADERS,
        timeout=12,
    )
    resp.raise_for_status()
    return resp.json() or []


def _fetch_trending(limit: int) -> List[Dict[str, Any]]:
    resp = requests.get(
        f"{COINGECKO_BASE}/search/trending",
        headers=DEFAULT_HEADERS,
        timeout=12,
    )
    resp.raise_for_status()
    data = resp.json() or {}
    coins = data.get("coins") or []
    result = []
    for item in coins[:limit]:
        coin = item.get("item") or {}
        result.append(
            {
                "id": coin.get("id"),
                "symbol": (coin.get("symbol") or "").upper(),
                "name": coin.get("name"),
                "market_cap_rank": coin.get("market_cap_rank"),
                "thumb": coin.get("thumb"),
                "score": coin.get("score"),
            }
        )
    return result


def _score_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Compute a lightweight 'smart money' signal score from momentum + liquidity.

    This is an educational heuristic, not a recommendation.
    """
    if not items:
        return items

    # Extract metrics for normalization
    changes = [abs(_safe_float(i.get("price_change_percentage_24h")) or 0.0) for i in items]
    volumes = [_safe_float(i.get("total_volume")) or 0.0 for i in items]
    mcaps = [_safe_float(i.get("market_cap")) or 0.0 for i in items]

    max_change = max(changes) or 1.0
    max_volume = max(volumes) or 1.0

    scored = []
    for item in items:
        change = abs(_safe_float(item.get("price_change_percentage_24h")) or 0.0)
        volume = _safe_float(item.get("total_volume")) or 0.0
        mcap = _safe_float(item.get("market_cap")) or 0.0
        liquidity = (volume / mcap) if mcap > 0 else 0.0

        momentum_score = min(change / max_change, 1.0)
        volume_score = min(volume / max_volume, 1.0)
        liquidity_score = min(liquidity * 5.0, 1.0)

        smart_score = round((0.45 * momentum_score + 0.35 * volume_score + 0.20 * liquidity_score) * 100, 2)

        scored.append(
            {
                **item,
                "smart_money_score": smart_score,
                "liquidity_score": round(liquidity_score * 100, 2),
            }
        )

    return scored


def _build_watchdog(items: List[Dict[str, Any]], limit: int) -> Dict[str, Any]:
    """Compute watchdog lists and risk flags from market data.

    Informational only; no investment advice.
    """
    def volume_ratio(coin: Dict[str, Any]) -> float:
        volume = _safe_float(coin.get("total_volume")) or 0.0
        mcap = _safe_float(coin.get("market_cap")) or 0.0
        return (volume / mcap) if mcap > 0 else 0.0

    enriched = []
    for coin in items:
        change = _safe_float(coin.get("price_change_percentage_24h")) or 0.0
        vol = _safe_float(coin.get("total_volume")) or 0.0
        mcap = _safe_float(coin.get("market_cap")) or 0.0
        ratio = volume_ratio(coin)

        flags = []
        if vol < 1_000_000:
            flags.append("low_liquidity")
        if mcap < 20_000_000:
            flags.append("micro_cap")
        if abs(change) > 30:
            flags.append("extreme_volatility")
        if ratio < 0.02:
            flags.append("thin_volume_ratio")
        if change > 40 and ratio > 0.2:
            flags.append("parabolic_spike")

        enriched.append({
            **coin,
            "volume_ratio": round(ratio, 4),
            "risk_flags": flags,
        })

    # Fast movers and decliners
    fast_movers = sorted(
        [c for c in enriched if (c.get("price_change_percentage_24h") or 0) > 0],
        key=lambda c: c.get("price_change_percentage_24h") or 0,
        reverse=True,
    )[:limit]

    fast_decliners = sorted(
        [c for c in enriched if (c.get("price_change_percentage_24h") or 0) < 0],
        key=lambda c: c.get("price_change_percentage_24h") or 0,
    )[:limit]

    # Unusual volume ratio (volume vs market cap)
    unusual_volume = sorted(
        enriched,
        key=lambda c: c.get("volume_ratio") or 0,
        reverse=True,
    )[:limit]

    # Emerging watchlist: smaller caps with meaningful volume and non-negative trend
    emerging_watch = []
    for coin in sorted(enriched, key=lambda c: c.get("market_cap") or 0):
        mcap = _safe_float(coin.get("market_cap")) or 0.0
        vol = _safe_float(coin.get("total_volume")) or 0.0
        change = _safe_float(coin.get("price_change_percentage_24h")) or 0.0
        if mcap < 2_000_000 or vol < 1_000_000:
            continue
        if change < -10:
            continue
        emerging_watch.append(coin)
        if len(emerging_watch) >= limit:
            break

    # Risk flags: coins with 2+ flags
    risk_flags = [c for c in enriched if len(c.get("risk_flags") or []) >= 2]
    risk_flags = sorted(risk_flags, key=lambda c: len(c.get("risk_flags") or []), reverse=True)[:limit]

    return {
        "fast_movers": fast_movers,
        "fast_decliners": fast_decliners,
        "unusual_volume": unusual_volume,
        "emerging_watch": emerging_watch,
        "risk_flags": risk_flags,
    }


@router.get("/crypto/overview")
def crypto_overview(limit: int = 20) -> Dict[str, Any]:
    limit = max(5, min(limit, 50))

    cache_key = f"overview:{limit}"
    cached = _cache_get(cache_key, ttl_seconds=60)
    if cached:
        return cached

    result: Dict[str, Any] = {
        "trending": [],
        "fast_movers": [],
        "emerging": [],
        "meta": {
            "source": "coingecko",
            "generated_at": int(time.time() * 1000),
            "not_investment_advice": True,
        },
    }

    try:
        result["trending"] = _fetch_trending(limit=min(limit, 15))
    except Exception:
        result["trending"] = []

    try:
        movers = _fetch_markets(order="price_change_percentage_24h_desc", per_page=limit)
        movers = [m for m in movers if (m.get("price_change_percentage_24h") or 0) > 0]
        result["fast_movers"] = _score_items(movers)[:limit]
    except Exception:
        result["fast_movers"] = []

    try:
        emerging = _fetch_markets(order="market_cap_asc", per_page=max(limit * 2, 20))
        filtered = []
        for item in emerging:
            mcap = _safe_float(item.get("market_cap")) or 0.0
            volume = _safe_float(item.get("total_volume")) or 0.0
            change = _safe_float(item.get("price_change_percentage_24h")) or 0.0
            if mcap < 2_000_000:
                continue
            if volume < 500_000:
                continue
            if change < -15:
                continue
            filtered.append(item)
            if len(filtered) >= limit:
                break

        result["emerging"] = _score_items(filtered)[:limit]
    except Exception:
        result["emerging"] = []

    _cache_set(cache_key, result)
    return result


@router.get("/crypto/watchdog")
def crypto_watchdog(limit: int = 20) -> Dict[str, Any]:
    limit = max(5, min(limit, 40))

    cache_key = f"watchdog:{limit}"
    cached = _cache_get(cache_key, ttl_seconds=60)
    if cached:
        return cached

    result: Dict[str, Any] = {
        "fast_movers": [],
        "fast_decliners": [],
        "unusual_volume": [],
        "emerging_watch": [],
        "risk_flags": [],
        "meta": {
            "source": "coingecko",
            "generated_at": int(time.time() * 1000),
            "not_investment_advice": True,
        },
    }

    try:
        markets = _fetch_markets(order="volume_desc", per_page=max(limit * 5, 100))
        watchdog = _build_watchdog(markets, limit)
        result.update(watchdog)
    except Exception:
        pass

    _cache_set(cache_key, result)
    return result
