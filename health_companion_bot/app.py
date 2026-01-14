from __future__ import annotations

import logging
from pathlib import Path

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from datetime import datetime

from .config import Settings, load_settings
from .handlers import (
    ASK_DATE,
    ASK_START,
    MAIN_MENU,
    cancel,
    on_document,
    on_menu_click,
    on_orphan_callback,
    on_photo,
    on_sleep_date,
    on_sleep_start,
    on_text,
    on_unknown,
    prompt_start,
    start,
)


def build_application(settings: Settings | None = None) -> Application:
    if settings is None:
        settings = load_settings()

    application = Application.builder().token(settings.bot_token).build()

    conversation = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(on_menu_click),
                MessageHandler(filters.PHOTO, on_photo),
                MessageHandler(filters.Document.ALL, on_document),
                MessageHandler(filters.TEXT & ~filters.COMMAND, on_text),
                MessageHandler(filters.ALL & ~filters.COMMAND, on_unknown),
            ],
            ASK_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_sleep_date)],
            ASK_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_sleep_start)],
        },
        fallbacks=[
            CommandHandler("start", start),
            CommandHandler("cancel", cancel),
        ],
    )
    application.add_handler(conversation)

    application.add_handler(CallbackQueryHandler(on_orphan_callback))
    application.add_handler(MessageHandler(filters.ALL, prompt_start))

    return application


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _configure_logging() -> None:
    log_path = _project_root() / "logs"
    log_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    log_file = log_path / f"health_companion_{timestamp}.log"
    handlers: list[logging.Handler] = [
        logging.StreamHandler(),
        logging.FileHandler(log_file, encoding="utf-8"),
    ]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )


def main() -> None:
    settings = load_settings()
    _configure_logging()
    # Игнорировать HTTP логи (показывать только WARNING и выше)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("telegram.bot").setLevel(logging.WARNING)
    logging.getLogger("telegram.ext").setLevel(logging.WARNING)
    logging.info("HealthCompanion успешно запущен! Добро пожаловать 🚀")
    build_application(settings).run_polling()
