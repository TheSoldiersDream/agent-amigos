"""Weather tools for Agent Amigos.

Uses Open-Meteo (no API key) for geocoding + forecast.
Docs:
- Geocoding: https://open-meteo.com/en/docs/geocoding-api
- Forecast:  https://open-meteo.com/en/docs

Design goals:
- "Live" = fetch current conditions from a public API at request time
- Deterministic, structured output suitable for LLM summarization
- Minimal PII: default location comes from environment variables (user-controlled)
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

import requests


@dataclass(frozen=True)
class _ResolvedLocation:
    name: str
    latitude: float
    longitude: float
    country: str | None = None
    admin1: str | None = None
    timezone: str | None = None
    geocoding_provider: str | None = None


_session = requests.Session()
_session.headers.update({"User-Agent": "AgentAmigos/1.0 (+local)"})


def _geocode_with_nominatim(name: str, timeout_s: float = 8.0) -> Optional[_ResolvedLocation]:
    """Fallback geocoder using OpenStreetMap Nominatim.

    Used only when Open-Meteo geocoding fails to resolve a query.

    Notes:
    - Keep request volume low (public service has strict usage limits)
    - Identify the application via User-Agent
    - Provide attribution in UI when using OSM data
    """
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": name,
        "format": "jsonv2",
        "addressdetails": 1,
        "limit": 1,
    }
    headers = {
        "User-Agent": "AgentAmigos/1.0 (local dev; geocoding fallback; contact: local)",
        "Accept-Language": "en",
    }
    r = _session.get(url, params=params, headers=headers, timeout=timeout_s)
    r.raise_for_status()
    results = r.json() or []
    if not results:
        return None
    top = results[0] or {}
    addr = top.get("address") or {}

    def _pick(*keys: str) -> Optional[str]:
        for k in keys:
            v = addr.get(k)
            if v:
                return str(v)
        return None

    return _ResolvedLocation(
        name=str(top.get("name") or top.get("display_name") or name),
        latitude=float(top["lat"]),
        longitude=float(top["lon"]),
        country=_pick("country"),
        admin1=_pick("state", "region", "province", "state_district"),
        timezone=None,
        geocoding_provider="openstreetmap-nominatim",
    )


def _env_default_location() -> str:
    loc = (os.getenv("WEATHER_DEFAULT_LOCATION") or "").strip()
    return loc or "Quezon City, Philippines"


def _open_meteo_units(units: str) -> dict[str, str]:
    u = (units or "metric").strip().lower()
    if u in {"metric", "si", "c"}:
        return {
            "temperature_unit": "celsius",
            "wind_speed_unit": "kmh",
            "precipitation_unit": "mm",
        }
    if u in {"imperial", "us", "f"}:
        return {
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
        }
    raise ValueError("units must be 'metric' or 'imperial'")


def _geocode_variants(name: str) -> Iterable[str]:
    """Generate increasingly less-specific variants of a location string.

    This makes geocoding more robust for very small localities that might not
    be present in the upstream gazetteer.
    """
    base = (name or "").strip()
    if not base:
        return []

    # 1) Try the full string first.
    variants: list[str] = [base]

    # 2) If comma-separated, progressively drop leading (most specific) parts.
    parts = [p.strip() for p in base.split(",") if p.strip()]
    if len(parts) >= 2:
        for i in range(1, len(parts) - 0):
            candidate = ", ".join(parts[i:])
            if candidate and candidate not in variants:
                variants.append(candidate)

        # 3) Also try the first 2-3 parts as a sometimes-better query.
        for take in (2, 3):
            if len(parts) >= take:
                candidate = ", ".join(parts[:take])
                if candidate and candidate not in variants:
                    variants.append(candidate)

    return variants


def _geocode_location(name: str, timeout_s: float = 8.0) -> _ResolvedLocation:
    url = "https://geocoding-api.open-meteo.com/v1/search"
    last_error: str | None = None
    tried: list[str] = []

    variants = list(_geocode_variants(name))
    if not variants:
        raise ValueError("Location name is empty")

    # 1) Try Open-Meteo geocoding for the full query (most precise if available).
    base = variants[0]
    tried.append(base)
    try:
        params = {
            "name": base,
            "count": 5,
            "language": "en",
            "format": "json",
        }
        r = _session.get(url, params=params, timeout=timeout_s)
        r.raise_for_status()
        data = r.json() or {}
        results = data.get("results") or []
        if results:
            top = results[0]
            return _ResolvedLocation(
                name=str(top.get("name") or base),
                latitude=float(top["latitude"]),
                longitude=float(top["longitude"]),
                country=(str(top.get("country")) if top.get("country") is not None else None),
                admin1=(str(top.get("admin1")) if top.get("admin1") is not None else None),
                timezone=(str(top.get("timezone")) if top.get("timezone") is not None else None),
                geocoding_provider="open-meteo-geocoding",
            )
    except Exception as e:
        last_error = str(e)

    # 2) If that fails, prefer Nominatim for the full query before trying broader fallbacks.
    try:
        loc = _geocode_with_nominatim(base, timeout_s=timeout_s)
        if loc is not None:
            return loc
    except Exception as e:
        last_error = str(e)

    # 3) Try less-specific Open-Meteo variants (bounded attempts to avoid "too broad" matches).
    for q in variants[1:4]:
        tried.append(q)
        params = {
            "name": q,
            "count": 5,
            "language": "en",
            "format": "json",
        }
        try:
            r = _session.get(url, params=params, timeout=timeout_s)
            r.raise_for_status()
            data = r.json() or {}
            results = data.get("results") or []
            if not results:
                continue
            top = results[0]
            return _ResolvedLocation(
                name=str(top.get("name") or q),
                latitude=float(top["latitude"]),
                longitude=float(top["longitude"]),
                country=(str(top.get("country")) if top.get("country") is not None else None),
                admin1=(str(top.get("admin1")) if top.get("admin1") is not None else None),
                timezone=(str(top.get("timezone")) if top.get("timezone") is not None else None),
                geocoding_provider="open-meteo-geocoding",
            )
        except Exception as e:
            last_error = str(e)

    # 4) Finally, try one additional Nominatim variant.
    if len(variants) > 1:
        try:
            loc = _geocode_with_nominatim(variants[1], timeout_s=timeout_s)
            if loc is not None:
                return loc
        except Exception as e:
            last_error = str(e)

    if last_error:
        raise ValueError(f"Could not geocode location: {name!r} ({last_error}). Tried: {tried}")
    raise ValueError(f"Could not geocode location: {name!r}. Tried: {tried}")


def _format_place(loc: _ResolvedLocation) -> str:
    parts = [loc.name]
    if loc.admin1:
        parts.append(loc.admin1)
    if loc.country:
        parts.append(loc.country)
    return ", ".join([p for p in parts if p])


class WeatherTools:
    """Weather-related tools."""

    def get_weather(
        self,
        location: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        units: str = "metric",
        forecast_days: int = 2,
        include_hourly: bool = False,
        include_solar: bool = False,
        pv_kw: Optional[float] = None,
        pv_performance_ratio: float = 0.8,
    ) -> Dict[str, Any]:
        """Get live weather for a location.

        Args:
            location: City/region name, e.g. "Quezon City, PH" or "London".
                      If omitted, uses WEATHER_DEFAULT_LOCATION.
            latitude/longitude: If provided, skips geocoding.
            units: metric|imperial
            forecast_days: 1..7
            include_hourly: If True, include hourly temperature/precip for the next day.

        Returns:
            Dict with success + structured weather data.
        """
        try:
            fd = int(forecast_days)
            if fd < 1:
                fd = 1
            if fd > 7:
                fd = 7

            unit_params = _open_meteo_units(units)

            resolved: _ResolvedLocation
            if latitude is not None and longitude is not None:
                resolved = _ResolvedLocation(
                    name=(location or "(coordinates)"),
                    latitude=float(latitude),
                    longitude=float(longitude),
                    geocoding_provider="coordinates",
                )
            else:
                loc_name = (location or "").strip() or _env_default_location()
                resolved = _geocode_location(loc_name)

            forecast_url = "https://api.open-meteo.com/v1/forecast"

            current_fields = [
                "temperature_2m",
                "relative_humidity_2m",
                "apparent_temperature",
                "precipitation",
                "cloud_cover",
                "weather_code",
                "wind_speed_10m",
                "wind_direction_10m",
            ]

            daily_fields = [
                "temperature_2m_max",
                "temperature_2m_min",
                "weather_code",
                "precipitation_sum",
                "rain_sum",
                "showers_sum",
                "precipitation_probability_max",
                "wind_speed_10m_max",
                "wind_gusts_10m_max",
            ]

            want_solar = bool(include_solar) or (pv_kw is not None)
            if want_solar:
                daily_fields.extend(
                    [
                        "sunrise",
                        "sunset",
                        "daylight_duration",
                        "sunshine_duration",
                        "shortwave_radiation_sum",
                        "uv_index_max",
                        "uv_index_clear_sky_max",
                    ]
                )

            params: Dict[str, Any] = {
                "latitude": resolved.latitude,
                "longitude": resolved.longitude,
                "current": ",".join(current_fields),
                "daily": ",".join(daily_fields),
                "forecast_days": fd,
                "timezone": "auto",
                **unit_params,
            }

            hourly_fields: list[str] = []
            if include_hourly:
                hourly_fields.extend(
                    [
                        "temperature_2m",
                        "precipitation",
                        "weather_code",
                        "wind_speed_10m",
                    ]
                )
            if want_solar:
                hourly_fields.extend(
                    [
                        "cloud_cover",
                        "cloud_cover_low",
                        "cloud_cover_mid",
                        "cloud_cover_high",
                    ]
                )

            if hourly_fields:
                # De-duplicate while preserving order.
                seen: set[str] = set()
                deduped: list[str] = []
                for f in hourly_fields:
                    if f not in seen:
                        seen.add(f)
                        deduped.append(f)
                params["hourly"] = ",".join(deduped)

            r = _session.get(forecast_url, params=params, timeout=10.0)
            r.raise_for_status()
            data = r.json() or {}

            derived: Dict[str, Any] = {}
            if want_solar:
                daily = data.get("daily") or {}
                daily_time = daily.get("time") or []
                sw_mj = daily.get("shortwave_radiation_sum") or []
                sunshine_s = daily.get("sunshine_duration") or []

                # Compute mean cloud cover per day from hourly values.
                hourly = data.get("hourly") or {}
                h_time = hourly.get("time") or []
                h_cloud = hourly.get("cloud_cover") or []
                cloud_sum: dict[str, float] = {}
                cloud_n: dict[str, int] = {}
                for t, c in zip(h_time, h_cloud):
                    if not t:
                        continue
                    day = str(t)[:10]
                    try:
                        cv = float(c)
                    except Exception:
                        continue
                    cloud_sum[day] = cloud_sum.get(day, 0.0) + cv
                    cloud_n[day] = cloud_n.get(day, 0) + 1
                cloud_mean = [
                    (cloud_sum.get(d, 0.0) / cloud_n.get(d, 1)) if cloud_n.get(d) else None
                    for d in daily_time
                ]

                # Convert MJ/m² to kWh/m² (1 kWh = 3.6 MJ)
                sw_kwh_m2: list[Optional[float]] = []
                for v in sw_mj:
                    try:
                        sw_kwh_m2.append(float(v) / 3.6)
                    except Exception:
                        sw_kwh_m2.append(None)

                sunshine_h: list[Optional[float]] = []
                for v in sunshine_s:
                    try:
                        sunshine_h.append(float(v) / 3600.0)
                    except Exception:
                        sunshine_h.append(None)

                pv_kw_f: Optional[float] = None
                if pv_kw is not None:
                    try:
                        pv_kw_f = float(pv_kw)
                    except Exception:
                        pv_kw_f = None
                pr = float(pv_performance_ratio) if pv_performance_ratio is not None else 0.8
                if pr < 0.1:
                    pr = 0.1
                if pr > 1.0:
                    pr = 1.0

                pv_kwh_per_kw: list[Optional[float]] = [
                    (v * pr) if v is not None else None for v in sw_kwh_m2
                ]
                pv_kwh: Optional[list[Optional[float]]] = None
                if pv_kw_f is not None:
                    pv_kwh = [
                        (pv_kw_f * v) if v is not None else None for v in pv_kwh_per_kw
                    ]

                derived = {
                    "daily": {
                        "time": daily_time,
                        "cloud_cover_mean": cloud_mean,
                        "shortwave_radiation_sum_kwh_m2": sw_kwh_m2,
                        "sunshine_duration_hours": sunshine_h,
                        "pv_estimated_kwh_per_kw": pv_kwh_per_kw,
                        "pv_estimated_kwh": pv_kwh,
                    },
                    "units": {
                        "cloud_cover_mean": "%",
                        "shortwave_radiation_sum_kwh_m2": "kWh/m²",
                        "sunshine_duration_hours": "h",
                        "pv_estimated_kwh_per_kw": "kWh/kW",
                        "pv_estimated_kwh": "kWh",
                    },
                    "assumptions": {
                        "pv_kw": pv_kw_f,
                        "pv_performance_ratio": pr,
                        "note": "PV estimates use daily shortwave radiation as a proxy for peak-sun-hours and a simple performance ratio. They are approximate.",
                    },
                }

            # Provide a stable, easy-to-summarize response.
            return {
                "success": True,
                "provider": "open-meteo",
                "requested_location": (location or "").strip() or None,
                "resolved_location": {
                    "place": _format_place(resolved),
                    "latitude": resolved.latitude,
                    "longitude": resolved.longitude,
                    "timezone": data.get("timezone"),
                    "geocoding_provider": resolved.geocoding_provider,
                },
                "units": {
                    "temperature": data.get("current_units", {}).get("temperature_2m"),
                    "wind_speed": data.get("current_units", {}).get("wind_speed_10m"),
                    "precipitation": data.get("current_units", {}).get("precipitation"),
                },
                "current": data.get("current"),
                "daily": data.get("daily"),
                "derived": derived or None,
                "fetched_at_unix": int(time.time()),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }


def resolve_location_name(name: str) -> str:
    """Public helper to verify and correct location spelling using geocoding."""
    if not name or not name.strip():
        return name
    try:
        resolved = _geocode_location(name.strip())
        return _format_place(resolved)
    except Exception:
        # Fallback to original name if geocoding fails
        return name


weather = WeatherTools()
