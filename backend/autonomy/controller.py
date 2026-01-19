import json
import os
from typing import Dict, Any
from datetime import datetime
from pathlib import Path
import time

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
CONFIG_PATH = os.path.join(ROOT_DIR, "agent.config.json")
LOG_DIR = os.path.join(ROOT_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "autonomous-agent.log")


DEFAULT_CONFIG: Dict[str, Any] = {
    "autonomyEnabled": False,
    "requireConfirmation": False,
    # When true, use the safe tools whitelist to auto-approve common non-destructive operations
    "autoApproveSafeTools": False,
    "allowedActions": [
        "filesystem",
        "terminal",
        "network-local",
        "code-modification",
        "canvas",
        "read-only",
        "memory",
        "search",
        "browser",
        "input",
        "screen",
        "clipboard",
        "notification",
        "general",
    ],
    "blockedActions": [
        "system-level-delete",
        "credential-exfiltration",
    ],
    "maxCommandDepth": 10,
    "mode": "FULL-AUTONOMY",  # Options: DRY-RUN, READ-ONLY, FULL-AUTONOMY
    "killSwitch": False,
    # New simplified autonomy mode: "off", "safe", "full"
    "autonomyMode": "off",
}


class AutonomyController:
    def __init__(self, config_path: str = CONFIG_PATH, log_file: str = LOG_FILE):
        self.config_path = config_path
        self.log_file = log_file
        self._config = DEFAULT_CONFIG.copy()
        # In-memory state for log throttling/rotation (avoid runaway logs).
        self._last_log_by_key: Dict[str, float] = {}
        self._load()
        self._ensure_logs()
        # Respect environment defaults if provided (useful for CI or dev overrides)
        try:
            env_enable = os.environ.get('AUTONOMY_ENABLE_BY_DEFAULT')
            if env_enable is not None:
                env_enable_bool = str(env_enable).lower() in ('1', 'true', 'yes', 'on')
                # Only override if the config file has not explicitly enabled autonomy
                if not self._config.get('autonomyEnabled') and env_enable_bool:
                    self._config['autonomyEnabled'] = True
            env_auto_approve = os.environ.get('AUTONOMY_AUTO_APPROVE_SAFE')
            if env_auto_approve is not None:
                self._config['autoApproveSafeTools'] = str(env_auto_approve).lower() in ('1', 'true', 'yes', 'on')
        except Exception:
            pass

    def _ensure_logs(self):
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        if not os.path.exists(self.log_file):
            with open(self.log_file, "w", encoding="utf-8") as fh:
                fh.write(f"[{datetime.utcnow().isoformat()}] Autonomy log created\n")

    def _rotate_logs_if_needed(self):
        """Rotate the autonomy log if it grows too large.

        This app can generate high-frequency entries (e.g., polling tasklist/ps),
        so we enforce a conservative size cap to prevent multi-GB log files.
        """
        try:
            max_bytes = int(os.environ.get("AUTONOMY_LOG_MAX_BYTES", str(50 * 1024 * 1024)))
        except Exception:
            max_bytes = 50 * 1024 * 1024

        try:
            if not os.path.exists(self.log_file):
                return
            size = os.path.getsize(self.log_file)
            if size <= max_bytes:
                return

            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            rotated = os.path.join(os.path.dirname(self.log_file), f"autonomous-agent.{ts}.log")
            try:
                os.replace(self.log_file, rotated)
            except Exception:
                # If rotation fails, do not crash logging.
                return

            # Keep only the newest N rotated logs.
            try:
                keep = int(os.environ.get("AUTONOMY_LOG_ROTATE_KEEP", "5"))
            except Exception:
                keep = 5
            if keep < 1:
                keep = 1

            folder = os.path.dirname(self.log_file)
            rotated_files = []
            for name in os.listdir(folder):
                if name.startswith("autonomous-agent.") and name.endswith(".log"):
                    rotated_files.append(os.path.join(folder, name))
            rotated_files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
            for old in rotated_files[keep:]:
                try:
                    os.remove(old)
                except Exception:
                    pass

            # Create a fresh log file.
            with open(self.log_file, "w", encoding="utf-8") as fh:
                fh.write(f"[{datetime.utcnow().isoformat()}] Autonomy log rotated (prev_bytes={size})\n")
        except Exception:
            # Never let logging/rotation crash the app.
            pass

    def _should_throttle(self, action: str, details: Dict[str, Any]) -> bool:
        """Return True if this entry should be dropped due to throttling."""
        try:
            # Only throttle known high-volume categories.
            if action not in {"terminal_popen", "terminal_command"}:
                return False

            cmd = str(details.get("cmd", ""))
            cmd_l = cmd.lower()

            # Default throttle for terminal logs (seconds).
            try:
                default_window = float(os.environ.get("AUTONOMY_TERMINAL_LOG_THROTTLE_SEC", "1.5"))
            except Exception:
                default_window = 1.5

            # Extra throttle for process polling utilities.
            window = default_window
            if "tasklist" in cmd_l or "ps" in cmd_l:
                try:
                    window = float(os.environ.get("AUTONOMY_POLL_LOG_THROTTLE_SEC", "15"))
                except Exception:
                    window = 15.0

            if window <= 0:
                return False

            key = f"{action}:{cmd_l}"
            now = time.monotonic()
            last = self._last_log_by_key.get(key)
            if last is not None and (now - last) < window:
                return True
            self._last_log_by_key[key] = now
            return False
        except Exception:
            return False

    def _load(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                    self._config.update(data)
            except Exception:
                # keep defaults
                pass
        else:
            self._save()

    def _save(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as fh:
            json.dump(self._config, fh, indent=2)

    def get_config(self) -> Dict[str, Any]:
        return self._config.copy()

    def set_config(self, new_config: Dict[str, Any]):
        self._config.update(new_config)
        self._save()

    def is_enabled(self) -> bool:
        mode = self._config.get("autonomyMode", "off")
        if mode == "off":
            return False
        return not self._config.get("killSwitch", False)

    def set_enabled(self, enabled: bool):
        self._config["autonomyEnabled"] = bool(enabled)
        self._save()

    def get_kill_switch(self) -> bool:
        return bool(self._config.get("killSwitch", False))

    def set_autonomy_mode(self, mode: str):
        if mode not in ["off", "safe", "full"]:
            raise ValueError("Invalid autonomy mode. Must be 'off', 'safe', or 'full'")
        self._config["autonomyMode"] = mode
        self._save()

    def is_action_allowed(self, action: str) -> bool:
        if self.get_kill_switch():
            return False
        mode = self._config.get("autonomyMode", "off")
        if mode == "off":
            return False
        allowed = self._config.get("allowedActions", [])
        blocked = self._config.get("blockedActions", [])
        if action in blocked:
            return False
        if mode == "full":
            return action in allowed or not allowed  # if allowed is empty, allow all
        elif mode == "safe":
            # Define safe actions
            safe_actions = ["read", "search", "web_search", "filesystem_read", "get_info", "network-local", "read-only", "map", "canvas", "memory", "screen", "clipboard", "notification"]
            return action in safe_actions and (action in allowed or not allowed)
        return False

    def get_allowed_actions(self) -> list:
        """Return list of allowed actions"""
        return self._config.get("allowedActions", [])

    def log_action(self, action: str, details: Dict[str, Any], result: Dict[str, Any] = None):
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        self._rotate_logs_if_needed()
        if self._should_throttle(action, details):
            return
        ts = datetime.utcnow().isoformat()
        entry = {
            "timestamp": ts,
            "action": action,
            "details": details,
            "result": result or {}
        }
        with open(self.log_file, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")


autonomy_controller = AutonomyController()
