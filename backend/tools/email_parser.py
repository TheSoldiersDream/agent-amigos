import re
from datetime import datetime
import uuid
import dateparser
from dateparser.search import search_dates

# Simple heuristic parser for travel emails (local-only, deterministic)
# Returns a structured itinerary dict.

# Airline flight numbers are typically 2-3 letter IATA/ICAO codes + digits (e.g., PR2042, JAL123).
# We use a heuristic to avoid matching airport codes followed by small numbers (common in UI noise).
FLIGHT_RE = re.compile(r"(?<![A-Z])(?:[A-Z]{2}\d{1,4}|[A-Z]{3}\s?\d{3,4})\b")
BOOKING_REF_RE = re.compile(r"Booking reference[:\s]*([A-Z0-9]+)", re.IGNORECASE)
ETICKET_RE = re.compile(r"E-?ticket number[:\s]*([\d-]+)", re.IGNORECASE)
AIRPORT_CODE_RE = re.compile(r"\b([A-Z]{3})\b")
# Avoid matching generic phrases like "enjoy your stay" by excluding the bare word "Stay".
HOTEL_RE = re.compile(r"Hotel|Accommodation|Resort|Apartment|Check-in|Check-out", re.IGNORECASE)
# Activity matcher is intentionally narrower than before to reduce false positives from
# generic words like "Booking" and "Confirmation" that appear in email footers.
ACTIVITY_RE = re.compile(r"Tour|Meeting|Dinner|Event|Appointment|Reservation|Visit|Show|Concert|Conference|Seminar|Workshop|Class|Lesson|Training|Match|Game|Restaurant|Cafe|Bar|Spa", re.IGNORECASE)
DATE_TIME_RE = re.compile(r"\b([A-Z][a-z]{2,8}\s\d{1,2}\s(?:[A-Z][a-z]{2}|[A-Za-z]{3,9})(?:\s\d{4})?)\b|\b(\d{1,2}\s[A-Za-z]{3,9}\s\d{4})\b|\b(\d{4}-\d{2}-\d{2})\b")

CHECKIN_RE = re.compile(r"(?im)^\s*Check-?in\s*[:\-]\s*(.+?)\s*$")
CHECKOUT_RE = re.compile(r"(?im)^\s*Check-?out\s*[:\-]\s*(.+?)\s*$")


def _clean_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _looks_like_noise(section_text: str) -> bool:
    """Heuristic to ignore Booking.com / newsletter footers and boilerplate blocks."""
    t = (section_text or "").lower()
    if not t.strip():
        return True

    # If the block contains strong travel signals, don't treat it as noise even if it
    # also includes footer/legal text (common in booking confirmation emails).
    try:
        if re.search(r"\([A-Z]{3}\)\s+to\s+.+\([A-Z]{3}\)", section_text or ""):
            return False
        if FLIGHT_RE.search(section_text or ""):
            return False
        if "booking reference" in t or "e-ticket" in t or "e ticket" in t:
            return False
        if "check-in" in t or "check out" in t or "check-out" in t:
            return False
    except Exception:
        pass

    noise_markers = [
        "privacy policy",
        "all rights reserved",
        "copyright",
        "manage booking",
        "why did i receive this",
        "unsubscribe",
        "oosterdokskade",
    ]
    if any(m in t for m in noise_markers):
        return True
    # Extremely long blocks are usually full email dumps, not a single segment.
    if len(t) > 2500:
        return True
    return False


def _dt_in_reasonable_range(dt: datetime) -> bool:
    try:
        return 2010 <= dt.year <= 2100
    except Exception:
        return False


def _extract_datetime_candidates(text: str):
    """Use dateparser's search to find candidate datetimes in a block, filtering noise."""
    if not text:
        return []
    try:
        found = search_dates(
            text,
            settings={
                "PREFER_DATES_FROM": "future",
                "RETURN_AS_TIMEZONE_AWARE": False,
            },
        )
    except Exception:
        found = None

    dts = []
    if found:
        for match_txt, dt in found:
            # Filter out common false positives from scraped email UI like "5 of 44".
            mt = (match_txt or "").strip()
            if mt and not re.search(
                r"(?i)(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)|\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}\s+[A-Za-z]{3,9}\b",
                mt,
            ):
                continue
            if isinstance(dt, datetime) and _dt_in_reasonable_range(dt):
                dts.append(dt)
    # de-dup while preserving order
    uniq = []
    seen = set()
    for dt in dts:
        key = dt.isoformat()
        if key in seen:
            continue
        seen.add(key)
        uniq.append(dt)
    return uniq


def _extract_checkin_checkout(raw_text: str):
    """Extract check-in and check-out datetimes from entire email body."""
    if not raw_text:
        return None, None
    cin = None
    cout = None
    m_in = CHECKIN_RE.search(raw_text)
    m_out = CHECKOUT_RE.search(raw_text)
    if m_in:
        cin = dateparser.parse(
            m_in.group(1).strip(),
            settings={"PREFER_DATES_FROM": "future", "RETURN_AS_TIMEZONE_AWARE": False},
        )
    if m_out:
        cout = dateparser.parse(
            m_out.group(1).strip(),
            settings={"PREFER_DATES_FROM": "future", "RETURN_AS_TIMEZONE_AWARE": False},
        )
    # Fallback: if not found by explicit labels, use candidates and take two distinct dates.
    if not cin or not cout:
        cands = _extract_datetime_candidates(raw_text)
        if cands:
            # Prefer the earliest as check-in, latest as check-out if both missing.
            if not cin:
                cin = cands[0]
            if not cout and len(cands) > 1:
                cout = cands[-1]
    if cin and not _dt_in_reasonable_range(cin):
        cin = None
    if cout and not _dt_in_reasonable_range(cout):
        cout = None
    # Ensure chronological order
    if cin and cout and cout < cin:
        cin, cout = cout, cin
    return cin, cout


def _strip_email_ui_noise(raw_text: str) -> str:
    """Remove common Gmail UI/header lines from copied emails to reduce parsing noise."""
    if not raw_text:
        return raw_text
    drop_exact = {
        "skip to content",
        "using gmail with screen readers",
        "inbox",
        "personal",
        "go to booking details",
    }
    cleaned_lines = []
    for line in raw_text.splitlines():
        s = (line or "").strip()
        if not s:
            cleaned_lines.append("")
            continue
        sl = s.lower()
        if sl in drop_exact:
            continue
        if sl.startswith("conversation opened"):
            continue
        if sl.startswith("label:"):
            continue
        # Gmail's "5 of 44" / "1 of 44" pager text.
        if re.match(r"^\d+\s+of\s+\d+$", sl):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def _parse_dates(text):
    # Try to find ISO-like or human readable dates and datetimes
    dates = []

    # Common airline/OTA format: 'Mon, Dec 29 • 12:55 PM - 2:15 PM'
    # (end time does not repeat the date).
    time_range_pat = re.compile(
        r"(?i)([A-Za-z]{3},?\s+[A-Za-z]{3}\s+\d{1,2})\s*[•·]\s*(\d{1,2}:\d{2}\s*[AP]M?)\s*[-–]\s*(\d{1,2}:\d{2}\s*[AP]M?)"
    )
    matches = time_range_pat.findall(text)
    if matches:
        for dpart, tstart, tend in matches:
            start_s = f"{dpart} {tstart}"
            end_s = f"{dpart} {tend}"
            ds = dateparser.parse(
                start_s,
                settings={"PREFER_DATES_FROM": "future", "RETURN_AS_TIMEZONE_AWARE": False},
            )
            de = dateparser.parse(
                end_s,
                settings={"PREFER_DATES_FROM": "future", "RETURN_AS_TIMEZONE_AWARE": False},
            )
            if ds and de:
                dates.append((ds, de) if ds <= de else (de, ds))
        if dates:
            return dates
    
    # Look for ranges with times: 'Mon 29 Dec · 12:55 - Mon 29 Dec · 16:05'
    # or '29 Dec 2025 12:55 - 29 Dec 2025 16:05'
    # or 'Check-in: Mon, Dec 29 ... Check-out: Wed, Dec 31'
    range_patterns = [
        r"([A-Za-z]{3,9}\s+\d{1,2}\s+[A-Za-z]{3}(?:\s+\d{4})?(?:\s+·\s+\d{2}:\d{2})?)\s*[·\-–]\s*([A-Za-z]{3,9}\s+\d{1,2}\s+[A-Za-z]{3}(?:\s+\d{4})?(?:\s+·\s+\d{2}:\d{2})?)",
        r"(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}(?:\s+\d{2}:\d{2})?)\s*[·\-–]\s*(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}(?:\s+\d{2}:\d{2})?)",
        r"(?i)Check-in:\s*([^\n]+).*?Check-out:\s*([^\n]+)"
    ]
    
    for pat in range_patterns:
        flags = re.DOTALL if "Check-in" in pat else 0
        ranges = re.findall(pat, text, flags=flags)
        if ranges:
            for a, b in ranges:
                # Clean up the '·' if present for dateparser
                da = dateparser.parse(
                    a.replace('·', ''),
                    settings={"PREFER_DATES_FROM": "future", "RETURN_AS_TIMEZONE_AWARE": False},
                )
                db = dateparser.parse(
                    b.replace('·', ''),
                    settings={"PREFER_DATES_FROM": "future", "RETURN_AS_TIMEZONE_AWARE": False},
                )
                if da and db:
                    dates.append((da, db))
            if dates:
                return dates

    # fallback: find single datelike expressions
    for match in DATE_TIME_RE.finditer(text):
        txt = match.group(0)
        dt = dateparser.parse(
            txt,
            settings={"PREFER_DATES_FROM": "future", "RETURN_AS_TIMEZONE_AWARE": False},
        )
        if dt:
            dates.append(dt)

    # last-chance: dateparser search across the block
    if not dates:
        cands = _extract_datetime_candidates(text)
        if cands:
            dates.extend(cands[:4])
    return dates


def parse_email_text(raw_text: str) -> dict:
    out = {
        "trip_id": f"itinerary-{uuid.uuid4().hex[:12]}",
        "source": "pasted-email",
        "summary": None,
        "passengers": [],
        "segments": [],
        "full_raw_text": raw_text,
        "start_date": None,
        "end_date": None,
    }

    # Work on a cleaned version for parsing, but keep the original for storage/debugging.
    parse_text = _strip_email_ui_noise(raw_text)

    # Booking references
    refs = BOOKING_REF_RE.findall(parse_text)
    if refs:
        out["booking_refs"] = refs

    # E-ticket numbers
    etickets = ETICKET_RE.findall(parse_text)
    if etickets:
        out["e_tickets"] = etickets

    # Passengers - heuristic: lines with full uppercase names or common name patterns
    pass_lines = []
    seen_names = set()
    for line in parse_text.splitlines():
        s = line.strip()
        if not s:
            continue
        # Filter out lines that look like seat info, flight routes, or labels
        if ":" in s or " - " in s or " – " in s or " | " in s:
            continue
        
        name_cand = None
        # All uppercase (likely name) and length > 4
        if s.isupper() and len(s) > 4 and re.search(r"[A-Z]", s):
            name_cand = s
        # Names in Title Case with two or three words
        elif re.match(r"^[A-Z][a-z]+\s[A-Z][a-z]+(?:\s[A-Z][a-z]+)?$", s):
            name_cand = s
            
        if name_cand and name_cand not in seen_names:
            # Final check: avoid common noise words, flight numbers, and booking refs
            noise = {
                "Inbox", "Personal", "Economy", "Philippine", "Airlines", "Booking", "Reference", 
                "Ticket", "Details", "Reservation", "Privacy", "Notice", "Statement", "Rights",
                "Accessibility", "Modern", "Slavery", "Human", "Review", "Awards", "Traveller",
                "Very", "Good", "Excellent", "Stay", "Check-in", "Check-out", "Property", "Room"
            }
            # If it matches a flight number or booking ref pattern, skip it
            if FLIGHT_RE.fullmatch(name_cand) or re.fullmatch(r"^[A-Z0-9]{6}$", name_cand):
                continue
            
            if not any(n in name_cand for n in noise):
                pass_lines.append(name_cand)
                seen_names.add(name_cand)

    if pass_lines:
        out["passengers"] = [{"name": p} for p in pass_lines]

    # Flights, Stays & Activities - find airline mentions, flight numbers, hotel keywords, or activity markers
    segments = []

    # Detect whether this email is likely about accommodation (as opposed to flight check-in).
    lodging_context = bool(re.search(r"(?i)\b(hotel|accommodation|property|room|nights)\b", parse_text or ""))
    # Split by common section headers and activity keywords
    # Avoid generic markers like "Booking"/"Confirmation" which cause noisy segments.
    markers = ["Returning flight", "Departing flight", "Flight", "Hotel", "Accommodation", "Check-in", "Check-out", "Reservation", "Tour", "Meeting", "Dinner", "Event", "Appointment"]
    pattern = "|".join([re.escape(m) for m in markers])
    sections = re.split(f"(?i)\\n\\s*({pattern})\\b", parse_text)

    # re.split with a capture group returns:
    #   [preamble_text, marker1, text_after1, marker2, text_after2, ...]
    # The preamble (index 0) is never a marker, even if it *contains* marker words.
    # If we treat it as a marker, we can misclassify (e.g., flight emails as stays).
    marker_pairs = []
    if len(sections) <= 1:
        # No recognizable markers; treat entire email as a single block.
        marker_pairs.append(("", parse_text))
    else:
        for j in range(1, len(sections), 2):
            marker_pairs.append((sections[j].strip(), sections[j + 1] if j + 1 < len(sections) else ""))

    for marker, sec in marker_pairs:

        if not sec.strip() and not marker:
            continue

        # Skip obvious boilerplate/footer chunks
        if _looks_like_noise(sec):
            continue
        
        fnums = FLIGHT_RE.findall(sec)
        if fnums:
            seen_f = set()
            fnums = [x for x in fnums if not (x in seen_f or seen_f.add(x))]

        airports = AIRPORT_CODE_RE.findall(sec)
        if airports:
            # Filter obvious non-airport tokens commonly found in footers/UI text.
            bad = {"FAQ", "WWW", "PDF"}
            airports = [a for a in airports if a not in bad]
            seen_a = set()
            airports = [x for x in airports if not (x in seen_a or seen_a.add(x))]
        # Include marker in the text block so label-based patterns work.
        dates = _parse_dates(f"{marker}\n{sec}")
        booking_ref = BOOKING_REF_RE.search(sec)
        eticket = ETICKET_RE.search(sec)
        # Use marker-driven detection to avoid false positives from phrases like
        # "enjoy your stay" in long email bodies.
        # Special case: Check-in/Check-out can refer to flight check-in; only treat as lodging when context supports it.
        if marker.lower() in ("check-in", "check-out"):
            is_hotel = lodging_context
        else:
            is_hotel = bool(HOTEL_RE.search(marker))
        is_activity = bool(ACTIVITY_RE.search(marker))

        seg = {}
        if is_hotel:
            seg["type"] = "stay"
            # Try to find hotel name (heuristic: first line of section if it's short)
            lines = sec.strip().splitlines()
            if lines:
                # Prefer a meaningful line: skip punctuation-only or date-only lines.
                hotel_name = marker
                for ln in lines[:12]:
                    cand = (ln or "").strip()
                    if not cand:
                        continue
                    if re.fullmatch(r"[:\-–—\s]+", cand):
                        continue
                    # Avoid using a bare date as a hotel name.
                    try:
                        maybe_dt = dateparser.parse(
                            cand,
                            settings={"PREFER_DATES_FROM": "future", "RETURN_AS_TIMEZONE_AWARE": False},
                        )
                    except Exception:
                        maybe_dt = None
                    if maybe_dt and len(cand) <= 40:
                        continue
                    if re.search(r"[A-Za-z]", cand):
                        hotel_name = cand[:80]
                        break
                seg["hotel_name"] = hotel_name
            else:
                seg["hotel_name"] = marker
        elif fnums or airports:
            seg["type"] = "flight"
            if fnums: seg["flight_numbers"] = fnums
            if airports:
                if len(airports) >= 2:
                    seg["legs"] = [{"from": airports[0], "to": airports[1]}]
                else:
                    seg["airports"] = airports
        elif "flight" in marker.lower():
            # Some airline/OTA confirmation emails don't include explicit flight numbers/airport codes.
            # If the marker indicates a flight section, create a flight segment anyway.
            seg["type"] = "flight"
        elif is_activity:
            seg["type"] = "activity"
            lines = sec.strip().splitlines()
            if lines and len(lines[0]) < 120:
                seg["activity_name"] = _clean_whitespace(lines[0])
            else:
                seg["activity_name"] = marker
        
        if seg:
            if dates:
                # Normalize any detected ranges to ensure start <= end.
                normalized = []
                for d in dates:
                    if isinstance(d, tuple) and len(d) >= 2 and isinstance(d[0], datetime) and isinstance(d[1], datetime):
                        a, b = d[0], d[1]
                        normalized.append((a, b) if a <= b else (b, a))
                    else:
                        normalized.append(d)
                seg["dates"] = normalized
            if booking_ref: seg["booking_reference"] = booking_ref.group(1)
            if eticket: seg["e_ticket"] = eticket.group(1)
            segments.append(seg)

    if segments:
        # Determine direction/order
        flight_count = 0
        for seg in segments:
            if seg["type"] == "flight":
                seg["direction"] = "outbound" if flight_count == 0 else "return"
                flight_count += 1
            out["segments"].append(seg)

    # Cross-segment enhancement: if we have a stay without dates, try check-in/check-out from the full email.
    cin, cout = (None, None)
    if lodging_context:
        cin, cout = _extract_checkin_checkout(parse_text)

    if cin or cout:
        for seg in out["segments"]:
            if seg.get("type") == "stay" and not seg.get("dates"):
                if cin and cout:
                    seg["dates"] = [(cin, cout)]
                elif cin:
                    seg["dates"] = [cin]

    # Extract global start/end dates for sorting and filtering
    all_dates = []
    for seg in out["segments"]:
        for d in seg.get("dates", []):
            if isinstance(d, tuple):
                all_dates.extend([d[0], d[1]])
            else:
                all_dates.append(d)
    
    if all_dates:
        valid_dates = [d for d in all_dates if d]
        if valid_dates:
            out["start_date"] = min(valid_dates).isoformat()
            out["end_date"] = max(valid_dates).isoformat()

    # Summary: create from detected airports/dates/hotels
    try:
        if out["segments"]:
            first = out["segments"][0]
            last = out["segments"][-1]
            s = []
            
            # Check for flights
            flights = [seg for seg in out["segments"] if seg["type"] == "flight"]
            if flights:
                f_first = flights[0]
                f_last = flights[-1]
                if f_first.get("legs"):
                    s.append(f"{f_first['legs'][0]['from']} → {f_first['legs'][0]['to']}")
                elif f_first.get("airports"):
                    s.append(" → ".join(f_first["airports"][:2]))
                
                if f_last != f_first:
                    if f_last.get("legs"):
                        s.append(f"{f_last['legs'][0]['from']} → {f_last['legs'][0]['to']}")
            
            # Check for stays
            stays = [seg for seg in out["segments"] if seg["type"] == "stay"]
            if stays:
                s.append(f"Stay at {stays[0].get('hotel_name', 'Hotel')}")

            # Check for activities
            activities = [seg for seg in out["segments"] if seg["type"] == "activity"]
            if activities:
                s.append(f"{activities[0].get('activity_name', 'Activity')}")
            
            # Use dates if present
            date_str = ""
            if out["start_date"]:
                sd = datetime.fromisoformat(out["start_date"]).strftime("%d %b %Y")
                ed = datetime.fromisoformat(out["end_date"]).strftime("%d %b %Y")
                date_str = f"{sd}" if sd == ed else f"{sd} — {ed}"
            
            out["summary"] = f"{', '.join(s)}{', ' + date_str if date_str else ''}".strip(', ')
    except Exception:
        pass

    return out
