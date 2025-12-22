from __future__ import annotations

import os
import dotenv
from dataclasses import dataclass

dotenv.load_dotenv()

@dataclass(frozen=True)
class Settings:
    bot_token: str


def load_settings() -> Settings:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not bot_token:
        raise RuntimeError(
            "Missing TELEGRAM_BOT_TOKEN env var. Example:\n"
            '  export TELEGRAM_BOT_TOKEN="123:ABC"\n'
            "Or copy `.env.example` and export it in your shell."
        )
    return Settings(bot_token=bot_token)

