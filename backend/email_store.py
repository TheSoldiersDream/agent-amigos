from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
import threading
import uuid
from typing import Dict, Any, Optional


def _safe_iso(dt: datetime) -> str:
    try:
        return dt.isoformat()
    except Exception:
        return str(dt)


def _fmt_date(dt: datetime) -> str:
    # Example: Sat, Dec 27, 2025
    return dt.strftime("%a, %b %d, %Y")


def _fmt_time(dt: datetime) -> str:
    return dt.strftime("%H:%M")


def _has_time_component(dt: datetime) -> bool:
    # dateparser often returns 00:00 when time is absent.
    try:
        return not (dt.hour == 0 and dt.minute == 0 and dt.second == 0)
    except Exception:
        return False

_store = {
    "itineraries": []
}

_LOCK = threading.RLock()

# Persist itineraries so the agent still has access after backend restarts.
_DATA_DIR = Path(__file__).resolve().parent / "data"
_DATA_DIR.mkdir(parents=True, exist_ok=True)
_STORE_PATH = _DATA_DIR / "email_itineraries.json"


def _dt_from_any(value) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        # Best effort: isoformat first.
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return None
    return None


def _serialize_dates(dates_value):
    """Serialize segment `dates` list into JSON-friendly values."""
    if not isinstance(dates_value, list):
        return dates_value
    out = []
    for entry in dates_value:
        if isinstance(entry, tuple) and len(entry) >= 2:
            start = _dt_from_any(entry[0])
            end = _dt_from_any(entry[1])
            out.append({
                "__kind__": "range",
                "start": _safe_iso(start) if start else None,
                "end": _safe_iso(end) if end else None,
            })
        else:
            dt = _dt_from_any(entry)
            out.append(_safe_iso(dt) if dt else (entry if isinstance(entry, (str, int, float, bool)) or entry is None else str(entry)))
    return out


def _deserialize_dates(dates_value):
    """Deserialize segment `dates` list from JSON into datetime/tuple."""
    if not isinstance(dates_value, list):
        return dates_value
    out = []
    for entry in dates_value:
        if isinstance(entry, dict) and entry.get("__kind__") == "range":
            start = _dt_from_any(entry.get("start"))
            end = _dt_from_any(entry.get("end"))
            if start and end:
                out.append((start, end))
            elif start:
                out.append(start)
            else:
                out.append(None)
        elif isinstance(entry, str):
            dt = _dt_from_any(entry)
            out.append(dt if dt else entry)
        else:
            out.append(entry)
    return out


def _serialize_itinerary(itin: Dict[str, Any]) -> Dict[str, Any]:
    # Shallow copy; ensure nested dates are JSON-friendly.
    data = dict(itin or {})
    segs = []
    for seg in (data.get("segments") or []):
        if not isinstance(seg, dict):
            continue
        seg2 = dict(seg)
        if "dates" in seg2:
            seg2["dates"] = _serialize_dates(seg2.get("dates"))
        segs.append(seg2)
    data["segments"] = segs
    return data


def _deserialize_itinerary(itin: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(itin or {})
    segs = []
    for seg in (data.get("segments") or []):
        if not isinstance(seg, dict):
            continue
        seg2 = dict(seg)
        if "dates" in seg2:
            seg2["dates"] = _deserialize_dates(seg2.get("dates"))
        segs.append(seg2)
    data["segments"] = segs
    return data


def _save_store() -> None:
    try:
        with _LOCK:
            payload = {
                "version": 1,
                "saved_at": datetime.utcnow().isoformat(),
                "itineraries": [_serialize_itinerary(i) for i in (_store.get("itineraries") or [])],
            }
            _STORE_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        # Never break API calls due to persistence failures.
        pass


def _load_store() -> None:
    try:
        if not _STORE_PATH.exists():
            return
        raw = _STORE_PATH.read_text(encoding="utf-8")
        payload = json.loads(raw)
        items = []
        if isinstance(payload, dict) and isinstance(payload.get("itineraries"), list):
            items = payload.get("itineraries")
        elif isinstance(payload, list):
            # Backwards compatible: file might just be a list
            items = payload
        items = items or []
        with _LOCK:
            _store["itineraries"] = [_deserialize_itinerary(i) for i in items if isinstance(i, dict)]
    except Exception:
        # Corrupt file or parse error: ignore and start fresh.
        pass


# Load persisted itineraries at import time.
_load_store()


def add_itinerary(itin: Dict[str, Any]) -> Dict[str, Any]:
    # Ensure unique id
    if "trip_id" not in itin:
        itin["trip_id"] = f"itinerary-{uuid.uuid4().hex[:12]}"
    with _LOCK:
        _store["itineraries"].append(itin)
        _save_store()
        return itin


def list_itineraries():
    # Sort by start_date if available
    def sort_key(it):
        sd = it.get("start_date")
        return sd if sd else "9999-12-31"
    with _LOCK:
        return sorted(list(_store["itineraries"]), key=sort_key)


def get_itinerary(it_id: str):
    with _LOCK:
        for it in _store["itineraries"]:
            if it.get("trip_id") == it_id:
                return it
        return None


def update_itinerary(it_id: str, new_itin: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Replace an existing itinerary (by trip_id) and persist changes."""
    if not it_id:
        return None
    if not isinstance(new_itin, dict):
        return None
    # Ensure trip_id stability
    new_itin = dict(new_itin)
    new_itin["trip_id"] = it_id
    with _LOCK:
        for idx, it in enumerate(_store["itineraries"]):
            if it.get("trip_id") == it_id:
                _store["itineraries"][idx] = new_itin
                _save_store()
                return new_itin
    return None


def delete_itinerary(it_id: str) -> bool:
    global _store
    with _LOCK:
        initial_len = len(_store["itineraries"])
        _store["itineraries"] = [it for it in _store["itineraries"] if it.get("trip_id") != it_id]
        changed = len(_store["itineraries"]) < initial_len
        if changed:
            _save_store()
        return changed


def generate_ics(itin: Dict[str, Any]) -> str:
    # Minimal .ics generator for the itinerary segments (flights as events)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//AgentAmigos//EmailItinerary//EN",
    ]

    for seg in itin.get("segments", []):
        # If we have dates as tuples, use first tuple
        dtstart = None
        dtend = None
        if seg.get("dates"):
            d = seg["dates"][0]
            if isinstance(d, tuple):
                # Use start and end datetimes if available
                dtstart = d[0]
                dtend = d[1]
            elif hasattr(d, "isoformat"):
                dtstart = d
        if dtstart:
            # Format naive as UTC-like YYYYMMDDTHHMMSSZ (no timezone conversion)
            def fmt(dt):
                return dt.strftime("%Y%m%dT%H%M%SZ") if hasattr(dt, "strftime") else ""
            uid = f"{itin.get('trip_id')}-{seg.get('direction','')}-{fmt(dtstart)}"
            lines.extend([
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{fmt(datetime.utcnow())}",
                f"DTSTART:{fmt(dtstart)}",
                f"DTEND:{fmt(dtend) if dtend else fmt(dtstart)}",
                f"SUMMARY:{seg.get('airline','Flight')}: {'/'.join(seg.get('flight_numbers',[]))}",
                "END:VEVENT",
            ])

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


def filter_itineraries_by_range(from_dt: datetime, to_dt: datetime):
    """Return itineraries that have at least one segment overlapping the given date range."""
    matched = []
    with _LOCK:
        itineraries = list(_store["itineraries"])

    for itin in itineraries:
        for seg in itin.get("segments", []):
            if not seg.get("dates"):
                continue

            d = seg["dates"][0]

            # normalize into (start, end)
            start = None
            end = None
            if isinstance(d, tuple) and len(d) >= 2:
                start = _dt_from_any(d[0])
                end = _dt_from_any(d[1])
            elif isinstance(d, dict) and d.get("__kind__") == "range":
                start = _dt_from_any(d.get("start"))
                end = _dt_from_any(d.get("end"))
            else:
                start = _dt_from_any(d)
                end = start

            if not start or not end:
                continue
            if from_dt and end < from_dt:
                continue
            if to_dt and start > to_dt:
                continue
            matched.append(itin)
            break
    return matched


def generate_combined_ics_for_itineraries(itineraries_list):
    """Generate a single .ics combining all flight events across the provided itineraries."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//AgentAmigos//CombinedItinerary//EN",
    ]
    for itin in itineraries_list:
        for seg in itin.get("segments", []):
            # Use the first date tuple if available
            if not seg.get("dates"):
                continue
            d = seg["dates"][0]
            if isinstance(d, tuple):
                dtstart = d[0]
                dtend = d[1]
            else:
                dtstart = d
                dtend = d
            if not hasattr(dtstart, "strftime"):
                continue
            def fmt(dt):
                return dt.strftime("%Y%m%dT%H%M%SZ")
            uid = f"{itin.get('trip_id')}-{seg.get('direction','')}-{fmt(dtstart)}"
            lines.extend([
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{fmt(datetime.utcnow())}",
                f"DTSTART:{fmt(dtstart)}",
                f"DTEND:{fmt(dtend) if dtend else fmt(dtstart)}",
                f"SUMMARY:{itin.get('summary','Trip')} - {seg.get('type','')}",
                f"DESCRIPTION:Booking refs: {itin.get('booking_refs', [])} | Passengers: {', '.join([p.get('name','') for p in itin.get('passengers',[])])}",
                "END:VEVENT",
            ])
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


def generate_text_summary_for_itineraries(itineraries_list, from_dt: Optional[datetime] = None, to_dt: Optional[datetime] = None) -> str:
    parts = []
    rng = ""
    if from_dt or to_dt:
        fr = from_dt.strftime("%Y-%m-%d") if from_dt else "*"
        to = to_dt.strftime("%Y-%m-%d") if to_dt else "*"
        rng = f" (Range: {fr} → {to})"
    parts.append(f"Combined itinerary summary{rng}\n")
    for itin in itineraries_list:
        parts.append(f"--- {itin.get('summary') or itin.get('trip_id')} ---")
        parts.append(f"Passengers: {', '.join([p.get('name','') for p in itin.get('passengers',[])])}")
        for seg in itin.get('segments', []):
            seg_desc = []
            if seg.get('direction'):
                seg_desc.append(seg['direction'])
            if seg.get('flight_numbers'):
                seg_desc.append('Flights: ' + ', '.join(seg['flight_numbers']))
            if seg.get('booking_reference'):
                seg_desc.append('Booking: ' + seg['booking_reference'])
            if seg.get('dates'):
                d = seg['dates'][0]
                if isinstance(d, tuple):
                    seg_desc.append(f"Dates: {d[0].isoformat()} → {d[1].isoformat()}")
                else:
                    seg_desc.append(f"Date: {d.isoformat()}")
            parts.append(' | '.join(seg_desc))
        parts.append('')
    return "\n".join(parts)


def generate_plain_english_timeline_for_itineraries(
    itineraries_list,
    from_dt: Optional[datetime] = None,
    to_dt: Optional[datetime] = None,
) -> str:
    """Generate a chronological, plain-English timeline across itineraries.

    Formatting goals:
    - Chronological, human-readable schedule grouped by day.
    - Expands multi-date segments (e.g. multi-leg flight emails) into multiple events.
    - Merges identical events across different saved emails to reduce duplicates.
    - Keeps stable ordering.
    """

    def _to_dt(v):
        if v is None:
            return None
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v)
            except Exception:
                return None
        return None

    def _expand_segment_occurrences(seg):
        """Return list of (start_dt, end_dt) occurrences from seg['dates']."""
        occ = []
        for d in (seg.get("dates") or []):
            if isinstance(d, tuple) and len(d) >= 2:
                s = _to_dt(d[0])
                e = _to_dt(d[1])
            else:
                s = _to_dt(d)
                e = _to_dt(d)
            if s is None:
                continue
            if e is None:
                e = s
            if e < s:
                s, e = e, s
            occ.append((s, e))
        return occ

    def _is_noisy_summary(s: Optional[str]) -> bool:
        if not s:
            return True
        t = str(s).strip()
        tl = t.lower()
        if not t:
            return True
        if "stay at check-in" in tl or "stay at check in" in tl:
            return True
        if tl == "details" or tl.endswith(", details") or "— details" in tl:
            return True
        if t == ":":
            return True
        return False

    def _trip_label(itin) -> str:
        summary = itin.get("summary")
        if summary and not _is_noisy_summary(summary):
            return str(summary)
        tid = str(itin.get("trip_id") or "Trip")
        if tid.startswith("itinerary-") and len(tid) > 18:
            return tid[:18] + "…"
        return tid

    def _event_key(seg, sdt, edt):
        """Key used to merge identical events across different itineraries."""
        seg_type = (seg.get("type") or "item").lower()
        booking = seg.get("booking_reference") or ""
        fn = "/".join(seg.get("flight_numbers") or [])
        legs = seg.get("legs") or []
        route = ""
        try:
            if legs and isinstance(legs, list):
                first = legs[0] or {}
                if first.get("from") and first.get("to"):
                    route = f"{first['from']}->{first['to']}"
        except Exception:
            route = ""
        stay = seg.get("hotel_name") or ""
        act = seg.get("activity_name") or ""
        return (
            seg_type,
            sdt.isoformat() if isinstance(sdt, datetime) else "",
            edt.isoformat() if isinstance(edt, datetime) else "",
            booking,
            fn,
            route,
            stay,
            act,
        )

    # Build merged event list
    merged: Dict[Any, Any] = {}
    undated = []

    for itin_idx, itin in enumerate(itineraries_list or []):
        segs = itin.get("segments", []) or []
        for seg_idx, seg in enumerate(segs):
            occ = _expand_segment_occurrences(seg)
            if not occ:
                undated.append({
                    "itinerary": itin,
                    "segment": seg,
                    "itin_idx": itin_idx,
                    "seg_idx": seg_idx,
                    "occ_idx": 0,
                    "start_dt": None,
                    "end_dt": None,
                })
                continue

            for occ_idx, (start_dt, end_dt) in enumerate(occ):
                key = _event_key(seg, start_dt, end_dt)
                label = _trip_label(itin)
                existing = merged.get(key)
                if existing is None:
                    merged[key] = {
                        "itinerary": itin,
                        "segment": seg,
                        "itin_idx": itin_idx,
                        "seg_idx": seg_idx,
                        "occ_idx": occ_idx,
                        "start_dt": start_dt,
                        "end_dt": end_dt,
                        "sources": [label] if label else [],
                    }
                else:
                    if (itin_idx, seg_idx, occ_idx) < (existing.get("itin_idx", 0), existing.get("seg_idx", 0), existing.get("occ_idx", 0)):
                        existing["itinerary"] = itin
                        existing["segment"] = seg
                        existing["itin_idx"] = itin_idx
                        existing["seg_idx"] = seg_idx
                        existing["occ_idx"] = occ_idx
                    if label and label not in existing.get("sources", []):
                        existing.setdefault("sources", []).append(label)

    events = list(merged.values())

    # Filter by range if requested
    def _in_range(item) -> bool:
        if not (from_dt or to_dt):
            return True
        s = item.get("start_dt")
        e = item.get("end_dt") or s
        if s is None:
            return False
        if from_dt and e and e < from_dt:
            return False
        if to_dt and s > to_dt:
            return False
        return True

    events = [e for e in events if _in_range(e)]

    # Sort
    events.sort(key=lambda e: (
        e["start_dt"],
        e.get("end_dt") or e["start_dt"],
        e["itin_idx"],
        e["seg_idx"],
        e.get("occ_idx", 0),
    ))

    # Group by date
    grouped = {}
    for e in events:
        day_key = e["start_dt"].date().isoformat()
        grouped.setdefault(day_key, []).append(e)

    # Render
    rng = ""
    if from_dt or to_dt:
        fr = from_dt.strftime("%Y-%m-%d") if from_dt else "*"
        to = to_dt.strftime("%Y-%m-%d") if to_dt else "*"
        rng = f" (Range: {fr} → {to})"

    lines = []
    lines.append(f"Itinerary timeline{rng}")

    if not events and not undated:
        lines.append("No itinerary items found.")
        return "\n".join(lines)

    if not events:
        lines.append("No dated itinerary items found in the selected range.")
    else:
        for day_key in sorted(grouped.keys()):
            day_dt = None
            try:
                day_dt = datetime.fromisoformat(day_key)
            except Exception:
                day_dt = None
            if day_dt:
                lines.append("")
                lines.append(_fmt_date(day_dt))
            else:
                lines.append("")
                lines.append(day_key)

            for e in grouped[day_key]:
                itin = e["itinerary"]
                seg = e["segment"]
                sdt = e["start_dt"]
                edt = e.get("end_dt")

                time_part = ""
                if sdt and _has_time_component(sdt):
                    if edt and _has_time_component(edt) and (edt != sdt):
                        if edt.date() != sdt.date():
                            # Cross-day ranges look confusing if we only show times.
                            time_part = f"{_fmt_time(sdt)}→{edt.strftime('%a %H:%M')} "
                        else:
                            time_part = f"{_fmt_time(sdt)}–{_fmt_time(edt)} "
                    else:
                        time_part = f"{_fmt_time(sdt)} "

                seg_type = (seg.get("type") or "item").lower()
                sources = e.get("sources") or []
                if len(sources) <= 1:
                    trip_label = sources[0] if sources else _trip_label(itin)
                else:
                    trip_label = f"{sources[0]} (+{len(sources) - 1} more)"

                # Build a clear sentence per segment
                text = ""
                if seg_type == "flight":
                    direction = seg.get("direction")
                    flight_nums = seg.get("flight_numbers") or []
                    legs = seg.get("legs") or []
                    route = ""
                    if legs and isinstance(legs, list) and legs[0].get("from") and legs[0].get("to"):
                        route = f"{legs[0]['from']} → {legs[0]['to']}"

                    bits = []
                    if direction:
                        bits.append(str(direction).capitalize())
                    bits.append("Flight")
                    if flight_nums:
                        bits.append("/".join(flight_nums))
                    if route:
                        bits.append(route)
                    text = " ".join(bits).strip()

                elif seg_type == "stay":
                    hotel = seg.get("hotel_name") or "Hotel stay"
                    # Avoid placeholder names like "Check-in" coming from section headers.
                    if str(hotel).strip().lower() in {"check-in", "check in", "check-out", "check out", ":"}:
                        hotel = "Accommodation"
                    # If we have an explicit range with dates, describe it
                    if sdt and edt and edt != sdt and (edt.date() != sdt.date()):
                        text = f"Stay: {hotel} ({sdt.date().isoformat()} → {edt.date().isoformat()})"
                    else:
                        text = f"Stay: {hotel}"

                elif seg_type == "activity":
                    name = seg.get("activity_name") or "Activity"
                    text = f"Activity: {name}"

                else:
                    text = f"{seg_type.capitalize()}: {trip_label}" if seg_type else str(trip_label)

                # Add booking reference if present
                if seg.get("booking_reference"):
                    text = f"{text} (Booking {seg['booking_reference']})"

                # Add passenger info if available
                passengers = itin.get("passengers") or []
                p_names = [p.get("name") for p in passengers if p.get("name")]
                who = f" [Who: {', '.join(p_names)}]" if p_names else ""

                lines.append(f"- {time_part}{text}{who} — {trip_label}")

    # Undated
    if undated:
        lines.append("")
        lines.append("Undated items")
        for item in undated:
            itin = item["itinerary"]
            seg = item["segment"]
            seg_type = (seg.get("type") or "item").lower()
            trip_label = _trip_label(itin)
            hint = ""
            if seg_type == "stay":
                hint = seg.get("hotel_name") or "Hotel stay"
            elif seg_type == "activity":
                hint = seg.get("activity_name") or "Activity"
            elif seg_type == "flight":
                nums = seg.get("flight_numbers") or []
                hint = "Flight " + "/".join(nums) if nums else "Flight"
            else:
                hint = seg_type.capitalize()

            # Add passenger info if available
            passengers = itin.get("passengers") or []
            p_names = [p.get("name") for p in passengers if p.get("name")]
            who = f" [Who: {', '.join(p_names)}]" if p_names else ""

            lines.append(f"- {hint}{who} — {trip_label} (no date found in email)")

    return "\n".join(lines)
