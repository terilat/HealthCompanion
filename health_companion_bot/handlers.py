from __future__ import annotations

import logging
from pathlib import Path
from typing import Final

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from .menu import MenuAction, build_main_menu_keyboard

logger = logging.getLogger(__name__)

STATE_KEY: Final[str] = "state"
STATE_MAIN_MENU: Final[str] = "MAIN_MENU"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _user_data_dir(user_id: int) -> Path:
    return _project_root() / "data" / "users" / str(user_id)


def _ensure_user_data_dir(user_id: int) -> Path:
    path = _user_data_dir(user_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _is_main_menu(context: ContextTypes.DEFAULT_TYPE) -> bool:
    return context.user_data.get(STATE_KEY) == STATE_MAIN_MENU


async def post_start_hook_stub(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user_dir: Path
) -> None:
    # TODO: place for custom initialization (DB, profiles, etc.)
    logger.info("post_start_hook_stub user_id=%s user_dir=%s", update.effective_user.id, user_dir)


async def process_image_stub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # TODO: replace with real image pipeline
    await update.effective_message.reply_text("Ок, изображение получено. (заглушка обработчика)")


async def process_text_stub(
    update: Update, context: ContextTypes.DEFAULT_TYPE, text: str
) -> None:
    # TODO: replace with real text pipeline
    await update.effective_message.reply_text("Ок, текст получен. (заглушка обработчика)")


async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data[STATE_KEY] = STATE_MAIN_MENU
    await update.effective_message.reply_text(
        "Главное меню:",
        reply_markup=build_main_menu_keyboard(),
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_dir = _ensure_user_data_dir(user.id)
    await post_start_hook_stub(update, context, user_dir)

    await update.effective_message.reply_text(
        f"Привет, {user.first_name}!\n\n"
        "Я HealthCompanion. Можешь отправлять текст и изображения.",
        parse_mode=ParseMode.HTML,
    )
    await send_main_menu(update, context)


async def on_menu_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return

    await query.answer()
    action = query.data or ""

    if action == MenuAction.HISTORY:
        context.user_data[STATE_KEY] = STATE_MAIN_MENU
        await query.message.reply_text("История данных: (заглушка)")
        return

    if action == MenuAction.ANALYSIS:
        context.user_data[STATE_KEY] = STATE_MAIN_MENU
        await query.message.reply_text("Анализ: (заглушка)")
        return

    if action == MenuAction.MAIN:
        await send_main_menu(update, context)
        return

    await query.message.reply_text("Неизвестная команда меню.")


def _document_looks_like_image(mime_type: str | None, file_name: str | None) -> bool:
    if mime_type and mime_type.startswith("image/"):
        return True
    if not file_name:
        return False
    lowered = file_name.lower()
    return lowered.endswith(
        (
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
            ".bmp",
            ".gif",
            ".tif",
            ".tiff",
            ".heic",
        )
    )


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_main_menu(context):
        await update.effective_message.reply_text("Нажми /start чтобы открыть главное меню.")
        return
    await process_image_stub(update, context)


async def on_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_main_menu(context):
        await update.effective_message.reply_text("Нажми /start чтобы открыть главное меню.")
        return

    message = update.effective_message
    document = getattr(message, "document", None)
    if not document:
        return

    if not _document_looks_like_image(document.mime_type, document.file_name):
        await message.reply_text("Пожалуйста, отправь файл-изображение (png/jpg/webp/...).")
        return

    await process_image_stub(update, context)


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_main_menu(context):
        await update.effective_message.reply_text("Нажми /start чтобы открыть главное меню.")
        return
    text = (update.effective_message.text or "").strip()
    await process_text_stub(update, context, text)


async def on_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_main_menu(context):
        await update.effective_message.reply_text("Нажми /start чтобы начать.")
        return
    await update.effective_message.reply_text("Не понял. Отправь текст или изображение.")

