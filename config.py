"""Private configuration shared by the controller and Windows agent."""

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_config(role):
    if role not in ("controller", "agent"):
        raise ValueError("Unknown configuration role")
    path = ROOT / "config.local.json"
    try:
        local = json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}
    except (OSError, ValueError):
        raise SystemExit("Cannot read config.local.json; check its JSON syntax and permissions.") from None
    if not isinstance(local, dict):
        raise SystemExit("config.local.json must contain a JSON object.")
    defaults = {"AGENT_TOKEN": "", "AGENT_PORT": 8765}
    if role == "controller":
        defaults.update(PC_NAME="PC", PC_IP="", PC_MAC="", WOL_SOURCE_IP="",
                        WOL_BROADCAST_IP="", HOMEKIT_PORT=51831,
                        PERSIST_FILE="pc_homekit.state", PINCODE="", POLL_INTERVAL=5)
    settings = {key: os.environ.get("PCH_" + key, local.get(key, value))
                for key, value in defaults.items()}
    for key, value in settings.items():
        if key in ("AGENT_PORT", "HOMEKIT_PORT", "POLL_INTERVAL"):
            if isinstance(value, bool) or not str(value).isdigit() or int(value) < 1:
                raise SystemExit(f"{key} must be a positive integer.")
            settings[key] = int(value)
            if key.endswith("PORT") and settings[key] > 65535:
                raise SystemExit(f"{key} must be at most 65535.")
        elif not isinstance(value, str) or not value.strip():
            raise SystemExit(f"Set {key} in config.local.json or PCH_{key} in the environment.")
    if role == "controller":
        if not re.fullmatch(r"[0-9]{3}-[0-9]{2}-[0-9]{3}", settings["PINCODE"]):
            raise SystemExit("PINCODE must use the format XXX-XX-XXX.")
        mac = re.sub(r"[:\- ]", "", settings["PC_MAC"])
        if not re.fullmatch(r"[0-9a-fA-F]{12}", mac):
            raise SystemExit("PC_MAC must contain a valid MAC address.")
        persist = Path(settings["PERSIST_FILE"]).expanduser()
        settings["PERSIST_FILE"] = str(persist if persist.is_absolute() else ROOT / persist)
    return settings
