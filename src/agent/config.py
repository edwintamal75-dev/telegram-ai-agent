from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _bool_from_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _admin_ids_from_env(value: str | None) -> set[int]:
    if not value:
        return set()
    admin_ids: set[int] = set()
    for item in value.split(","):
        item = item.strip()
        if item:
            admin_ids.add(int(item))
    return admin_ids


def _load_env_file(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


@dataclass(frozen=True)
class Settings:
    app_name: str
    dry_run: bool
    openai_api_key: str
    openai_model: str
    telegram_bot_token: str
    telegram_channel_id: str
    telegram_allowed_admin_ids: set[int]
    database_path: Path
    default_timezone: str
    auto_reply_enabled: bool

    @property
    def openai_ready(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def telegram_ready(self) -> bool:
        return bool(self.telegram_bot_token)


def load_settings() -> Settings:
    _load_env_file()
    return Settings(
        app_name=os.getenv("APP_NAME", "Telegram AI Agent"),
        dry_run=_bool_from_env("DRY_RUN", True),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_channel_id=os.getenv("TELEGRAM_CHANNEL_ID", ""),
        telegram_allowed_admin_ids=_admin_ids_from_env(os.getenv("TELEGRAM_ALLOWED_ADMIN_IDS")),
        database_path=Path(os.getenv("DATABASE_PATH", "data/agent.sqlite3")),
        default_timezone=os.getenv("DEFAULT_TIMEZONE", "Asia/Bangkok"),
        auto_reply_enabled=_bool_from_env("AUTO_REPLY_ENABLED", True),
    )
