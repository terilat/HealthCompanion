from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    bot_token: str = Field(
        ...,
        min_length=1,
        description="Telegram bot token",
        validation_alias="TELEGRAM_BOT_TOKEN",
    )

def load_settings() -> Settings:
    try:
        return Settings()
    except Exception as e:
        raise RuntimeError(
            "Missing or invalid TELEGRAM_BOT_TOKEN env var. Example:\n"
            '  export TELEGRAM_BOT_TOKEN="123:ABC"\n'
            "Or copy `.env.example` and export it in your shell."
        ) from e
