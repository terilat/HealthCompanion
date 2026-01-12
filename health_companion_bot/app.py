from __future__ import annotations

import logging

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from .config import load_settings
from .handlers import (
    ASK_DATE,
    ASK_END,
    ASK_START,
    MAIN_MENU,
    cancel,
    on_document,
    on_menu_click,
    on_orphan_callback,
    on_photo,
    on_sleep_date,
    on_sleep_end,
    on_sleep_start,
    on_text,
    on_unknown,
    prompt_start,
    start,
)


def build_application() -> Application:
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
            ASK_END: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_sleep_end)],
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


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )    
    # Игнорировать HTTP логи (показывать только WARNING и выше)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("telegram.bot").setLevel(logging.WARNING)
    logging.getLogger("telegram.ext").setLevel(logging.WARNING)
    build_application().run_polling()
