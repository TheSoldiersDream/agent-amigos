from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
import threading
from typing import Dict, Any, List

_LOCK = threading.RLock()
_DATA_DIR = Path(__file__).resolve().parent / "data"
_DATA_DIR.mkdir(parents=True, exist_ok=True)
_STORE_PATH = _DATA_DIR / "marketing_leads.json"

_store: Dict[str, Any] = {"leads": []}


def _load_store() -> None:
    if not _STORE_PATH.exists():
        return
    try:
        raw = _STORE_PATH.read_text(encoding="utf-8")
        payload = json.loads(raw)
        if isinstance(payload, dict) and isinstance(payload.get("leads"), list):
            _store["leads"] = payload.get("leads", [])
    except Exception:
        return


def _save_store() -> None:
    try:
        payload = {
            "version": 1,
            "saved_at": datetime.utcnow().isoformat(),
            "leads": _store.get("leads", []),
        }
        _STORE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception:
        return


_load_store()


def list_leads() -> List[Dict[str, Any]]:
    with _LOCK:
        return list(_store.get("leads", []))


def add_lead(email: str, name: str | None = None, source: str | None = None, meta: Dict[str, Any] | None = None) -> Dict[str, Any]:
    if not email:
        raise ValueError("email required")
    normalized = email.strip().lower()
    now = datetime.utcnow().isoformat()
    with _LOCK:
        for lead in _store.get("leads", []):
            if lead.get("email") == normalized:
                lead["last_seen"] = now
                lead["count"] = int(lead.get("count", 1)) + 1
                if name:
                    lead["name"] = name
                if source:
                    lead["source"] = source
                if meta and isinstance(meta, dict):
                    lead["meta"] = {**lead.get("meta", {}), **meta}
                _save_store()
                return lead
        lead = {
            "email": normalized,
            "name": name or "",
            "source": source or "",
            "meta": meta or {},
            "created_at": now,
            "last_seen": now,
            "count": 1,
        }
        _store.setdefault("leads", []).append(lead)
        _save_store()
        return lead
