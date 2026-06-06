"""
Config önce environment variable'lardan okur (Railway/bulut için),
bulamazsa config.yaml'a düşer (lokal geliştirme için).
"""

import os
import yaml
from pathlib import Path


def load() -> dict:
    base = _load_yaml()

    # Telegram
    base.setdefault("telegram", {})
    base["telegram"]["bot_token"] = os.getenv("TELEGRAM_BOT_TOKEN", base["telegram"].get("bot_token", ""))
    base["telegram"]["chat_id"]   = os.getenv("TELEGRAM_CHAT_ID",   base["telegram"].get("chat_id", ""))

    # Email
    base.setdefault("email", {})
    base["email"]["sender"]      = os.getenv("EMAIL_SENDER",   base["email"].get("sender", ""))
    base["email"]["password"]    = os.getenv("EMAIL_PASSWORD", base["email"].get("password", ""))
    base["email"]["smtp_server"] = os.getenv("EMAIL_SMTP",     base["email"].get("smtp_server", "smtp.gmail.com"))
    base["email"]["smtp_port"]   = int(os.getenv("EMAIL_PORT", base["email"].get("smtp_port", 587)))
    recipients_env = os.getenv("EMAIL_RECIPIENTS")
    if recipients_env:
        base["email"]["recipients"] = [r.strip() for r in recipients_env.split(",")]
    base["email"]["enabled"] = bool(base["email"].get("sender"))

    # Genel ayarlar
    base["check_interval_minutes"] = int(
        os.getenv("CHECK_INTERVAL_MINUTES", base.get("check_interval_minutes", 5))
    )
    base["headless"] = os.getenv("HEADLESS", "true").lower() != "false"

    return base


def _load_yaml() -> dict:
    path = Path(__file__).parent / "config.yaml"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}
