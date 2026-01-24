"""Trading bot routes (paper-mode by default).

This is intentionally a *simulation/stub* implementation designed to power the
Trading Bot Console UI. It does NOT place real trades.

Future work:
- exchange connectors (ccxt or native)
- strategy engine plugins
- persistent storage for runs/trades
- SSE/WebSocket streaming for events
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
import time
import uuid

router = APIRouter(prefix="/trading", tags=["trading"])


def _now_ms() -> int:
    return int(time.time() * 1000)


def _event(kind: str, message: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "ts": _now_ms(),
        "kind": kind,
        "message": message,
        "data": data or {},
    }


# In-memory state (process-local). Safe default: paper trading.
_STATE: Dict[str, Any] = {
    "mode": "paper",  # paper | live (live not implemented)
    "running": False,
    "symbols": ["BTCUSDT", "ETHUSDT"],
    "risk": {
        "risk_per_trade_pct": 0.5,
        "max_daily_loss_pct": 2.0,
        "max_open_positions": 3,
        "confidence_threshold": 0.72,
        "kill_switch": False,
    },
    "agents": {
        "market_scanner": {"status": "idle", "confidence": 0.0},
        "signal_validator": {"status": "idle", "confidence": 0.0},
        "risk_officer": {"status": "idle", "confidence": 0.0},
        "execution": {"status": "idle", "confidence": 0.0},
        "auditor": {"status": "idle", "confidence": 0.0},
    },
    "account": {
        "balance": 10000.0,
        "currency": "USD",
        "daily_pnl": 0.0,
        "drawdown_pct": 0.0,
        "risk_exposure_pct": 0.0,
    },
    "trades": [],
    "events": [],
    "last_trade": None,
    "last_decision": None,
}


class CommandRequest(BaseModel):
    command: str = Field(..., min_length=1)
    context: Optional[Dict[str, Any]] = None


class CommandResponse(BaseModel):
    ok: bool
    reply: str
    events: List[Dict[str, Any]] = []
    state: Dict[str, Any] = {}


class RiskConfig(BaseModel):
    risk_per_trade_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    max_daily_loss_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    max_open_positions: Optional[int] = Field(default=None, ge=0)
    confidence_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    kill_switch: Optional[bool] = None


@router.get("/status")
def get_status() -> Dict[str, Any]:
    return {
        "mode": _STATE["mode"],
        "running": _STATE["running"],
        "symbols": _STATE["symbols"],
        "risk": _STATE["risk"],
        "agents": _STATE["agents"],
        "account": _STATE["account"],
        "last_trade": _STATE["last_trade"],
        "last_decision": _STATE["last_decision"],
        "ts": _now_ms(),
    }


@router.get("/dashboard")
def get_dashboard() -> Dict[str, Any]:
    # In a real system these would be computed from fills, mark prices, etc.
    return {
        "account": _STATE["account"],
        "market": {
            "symbols_monitored": _STATE["symbols"],
            "volatility_index": 0.42,
            "liquidity_score": 0.77,
            "news_sentiment": 0.12,
        },
        "agent_status": {
            "active_agents": [k for k, v in _STATE["agents"].items() if v.get("status") != "idle"],
            "last_decision_time_ms": _STATE["last_decision"]["ts"] if _STATE.get("last_decision") else None,
            "execution_latency_ms": 120,
        },
        "ts": _now_ms(),
    }


@router.get("/trades")
def list_trades(limit: int = 200) -> Dict[str, Any]:
    trades = list(reversed(_STATE["trades"]))[: max(1, min(limit, 500))]
    return {"trades": trades, "ts": _now_ms()}


@router.get("/events")
def list_events(limit: int = 200) -> Dict[str, Any]:
    ev = list(reversed(_STATE["events"]))[: max(1, min(limit, 500))]
    return {"events": ev, "ts": _now_ms()}


@router.get("/risk")
def get_risk() -> Dict[str, Any]:
    return {"risk": _STATE["risk"], "ts": _now_ms()}


@router.post("/risk")
def set_risk(cfg: RiskConfig) -> Dict[str, Any]:
    changed = {}
    for k, v in cfg.model_dump(exclude_none=True).items():
        _STATE["risk"][k] = v
        changed[k] = v

    evt = _event("risk", "Risk config updated", {"changed": changed})
    _STATE["events"].append(evt)
    return {"ok": True, "risk": _STATE["risk"], "event": evt, "ts": _now_ms()}


def _make_fake_trade(symbol: str = "BTCUSDT", side: str = "BUY") -> Dict[str, Any]:
    # A tiny stub trade record.
    entry = 42000.0 if symbol.startswith("BTC") else 2200.0
    size = 0.01 if symbol.startswith("BTC") else 0.1
    trade = {
        "id": str(uuid.uuid4()),
        "ts": _now_ms(),
        "symbol": symbol,
        "side": side,
        "size": size,
        "entry": entry,
        "sl": entry * (0.99 if side == "BUY" else 1.01),
        "tp": entry * (1.02 if side == "BUY" else 0.98),
        "agent_confidence": 0.78,
        "entry_reason": "Trend-follow setup: higher-high + volume expansion; risk approved by Risk Officer.",
        "mode": _STATE["mode"],
        "pnl": 0.0,
    }
    return trade


def _explain_last_trade() -> str:
    t = _STATE.get("last_trade")
    if not t:
        return "No trades yet. Run `/start trading BTCUSDT` (paper) to generate a simulated execution."

    return (
        "Last trade explainability:\n"
        f"• Symbol: {t.get('symbol')}\n"
        f"• Direction: {t.get('side')}\n"
        f"• Size: {t.get('size')}\n"
        f"• Strategy: trend_follow (stub)\n"
        f"• Confidence: {t.get('agent_confidence')}\n"
        f"• Why now: breakout confirmation + validator agreement\n"
        f"• Risk checks: risk_per_trade_pct={_STATE['risk'].get('risk_per_trade_pct')}%, max_daily_loss_pct={_STATE['risk'].get('max_daily_loss_pct')}%\n"
        f"• What could go wrong: false breakout; volatility spike; slippage\n"
    )


@router.post("/command", response_model=CommandResponse)
def run_command(req: CommandRequest) -> CommandResponse:
    cmd = (req.command or "").strip()
    if not cmd:
        return CommandResponse(ok=False, reply="Empty command", events=[], state={})

    # Normalize common variants
    lower = cmd.lower().strip()
    new_events: List[Dict[str, Any]] = []

    # Global safety
    if _STATE["risk"].get("kill_switch") and not lower.startswith("/risk"):
        evt = _event("blocked", "Kill switch active: trading commands blocked", {"command": cmd})
        _STATE["events"].append(evt)
        return CommandResponse(
            ok=False,
            reply="Kill switch active. Use `/risk kill off` to re-enable (paper).",
            events=[evt],
            state=get_status(),
        )

    def emit(kind: str, msg: str, data: Optional[Dict[str, Any]] = None) -> None:
        e = _event(kind, msg, data)
        _STATE["events"].append(e)
        new_events.append(e)

    # Commands
    if lower.startswith("/start"):
        _STATE["running"] = True
        emit("system", "Trading agent started (paper mode)", {"mode": _STATE["mode"]})

        # Optional symbol in command: /start trading BTCUSDT
        tokens = lower.split()
        if len(tokens) >= 3:
            symbol = tokens[2].upper()
            if symbol not in _STATE["symbols"]:
                _STATE["symbols"].append(symbol)
                emit("config", f"Added symbol {symbol}", {"symbol": symbol})

        # Generate a simulated trade to populate UI
        symbol = (_STATE["symbols"][0] if _STATE["symbols"] else "BTCUSDT")
        trade = _make_fake_trade(symbol=symbol, side="BUY")
        _STATE["trades"].append(trade)
        _STATE["last_trade"] = trade
        _STATE["last_decision"] = {
            "ts": _now_ms(),
            "summary": f"Entered {trade['side']} {trade['symbol']} (paper) with SL/TP.",
            "strategy": "trend_follow",
            "signals": [
                {"name": "hh_hl_structure", "weight": 0.35, "score": 0.82},
                {"name": "volume_expansion", "weight": 0.25, "score": 0.74},
                {"name": "momentum_filter", "weight": 0.20, "score": 0.70},
            ],
            "rejected_signals": [
                {"name": "mean_reversion", "reason": "regime trending"},
            ],
            "risk_officer": {
                "approved": True,
                "notes": "Sizing within risk_per_trade_pct; SL distance sane.",
            },
        }
        emit("trade", f"Simulated trade opened: {trade['side']} {trade['symbol']}", {"trade": trade})

        return CommandResponse(ok=True, reply="Bot started (paper).", events=new_events, state=get_status())

    if lower.startswith("/pause"):
        _STATE["running"] = False
        emit("system", "Trading paused", {})
        return CommandResponse(ok=True, reply="Trading paused.", events=new_events, state=get_status())

    if lower.startswith("/risk report"):
        reply = (
            "Risk report:\n"
            f"• risk_per_trade_pct: {_STATE['risk'].get('risk_per_trade_pct')}%\n"
            f"• max_daily_loss_pct: {_STATE['risk'].get('max_daily_loss_pct')}%\n"
            f"• max_open_positions: {_STATE['risk'].get('max_open_positions')}\n"
            f"• confidence_threshold: {_STATE['risk'].get('confidence_threshold')}\n"
            f"• kill_switch: {_STATE['risk'].get('kill_switch')}\n"
        )
        emit("risk", "Risk report requested", {})
        return CommandResponse(ok=True, reply=reply, events=new_events, state=get_status())

    if lower.startswith("/why"):
        emit("explain", "Explainability requested", {"command": cmd})
        return CommandResponse(ok=True, reply=_explain_last_trade(), events=new_events, state=get_status())

    if lower.startswith("/risk kill"):
        # /risk kill on|off
        parts = lower.split()
        if len(parts) >= 3 and parts[2] in {"on", "off"}:
            _STATE["risk"]["kill_switch"] = parts[2] == "on"
            emit("risk", f"Kill switch set to {parts[2]}", {"kill_switch": _STATE["risk"]["kill_switch"]})
            return CommandResponse(ok=True, reply=f"Kill switch: {parts[2]}", events=new_events, state=get_status())
        return CommandResponse(ok=False, reply="Usage: /risk kill on|off", events=new_events, state=get_status())

    emit("unknown", "Unknown command", {"command": cmd})
    return CommandResponse(
        ok=False,
        reply="Unknown command. Try: /start trading BTCUSDT, /pause trading, /risk report, /why last trade",
        events=new_events,
        state=get_status(),
    )
