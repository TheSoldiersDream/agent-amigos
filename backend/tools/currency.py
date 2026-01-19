"""Currency conversion helpers using exchangerate.host (free, no API key).

Provides cached rates and simple conversion helpers.
"""
from __future__ import annotations

import time
import requests
import os
from typing import Dict, Optional

_CACHE = {
    "rates": {},
    "ts": 0,
    "base": "EUR",
}

_DEFAULT_TTL = int(os.environ.get("CURRENCY_RATE_TTL", "3600"))  # seconds
_API = "https://api.exchangerate.host/latest"


def _fetch_rates(base: str = "EUR") -> Dict[str, float]:
    params = {"base": base}
    resp = requests.get(_API, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json() or {}
    rates = data.get("rates") or {}
    return rates


def _ensure_rates(base: str = "EUR") -> None:
    now = int(time.time())
    if (_CACHE.get("ts", 0) + _DEFAULT_TTL) > now and _CACHE.get("base") == base and _CACHE.get("rates"):
        return
    rates = _fetch_rates(base=base)
    _CACHE["rates"] = rates
    _CACHE["ts"] = now
    _CACHE["base"] = base


def convert(amount: float, from_currency: str, to_currency: str) -> Optional[float]:
    """Convert amount from one currency to another. Returns rounded float or None on error."""
    try:
        from_currency = (from_currency or "").upper()
        to_currency = (to_currency or "").upper()
        if from_currency == to_currency:
            return round(float(amount), 2)
        # Use EUR as fetching base for performance; if from_currency != base, fetch with base=from_currency
        _ensure_rates(base=from_currency)
        rates = _CACHE.get("rates") or {}
        rate = rates.get(to_currency)
        if rate is None:
            # try fetching with EUR base and compute cross-rate
            _ensure_rates(base="EUR")
            rates = _CACHE.get("rates") or {}
            from_rate = rates.get(from_currency)
            to_rate = rates.get(to_currency)
            if not from_rate or not to_rate:
                return None
            # amount in EUR then to target
            eur_amount = float(amount) / float(from_rate)
            return round(eur_amount * float(to_rate), 2)
        return round(float(amount) * float(rate), 2)
    except Exception:
        return None


def format_currency(amount: float, currency: str) -> str:
    try:
        return f"{currency.upper()} {amount:,.2f}"
    except Exception:
        return f"{amount} {currency.upper()}"