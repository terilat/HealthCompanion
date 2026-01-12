from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, ConversationHandler

from .menu import MenuAction, build_main_menu_keyboard

from .llm_processor import extract_health_data, SleepLog

logger = logging.getLogger(__name__)

MAIN_MENU = 1


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _user_data_dir(user_id: int | str) -> Path:
    return _project_root() / "data" / "users" / str(user_id)


def _ensure_user_data_dir(user_id: int | str) -> Path:
    path = _user_data_dir(user_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


async def post_start_hook_stub(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user_dir: Path
) -> None:
    # TODO: place for custom initialization (DB, profiles, etc.)
    logger.info("post_start_hook_stub user_id=%s user_dir=%s", update.effective_user.id, user_dir)


async def process_image_stub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает изображение от пользователя:
    1. Сохраняет фото в директорию пользователя
    2. Формирует промпт для LLM
    3. Извлекает данные о здоровье через LLM
    4. Отправляет результат пользователю
    """
    user_id = update.effective_user.id
    user_dir = _ensure_user_data_dir(user_id)
    bot = context.bot
    message = update.effective_message
    
    # Получаем файл фото
    photo_file = None
    file_extension = ".jpg"
    
    # Проверяем, пришло ли фото как photo или как document
    if message.photo:
        # Берем самое большое фото
        photo_file = message.photo[-1]
        file_extension = ".jpg"
    elif message.document:
        photo_file = message.document
        # Определяем расширение из имени файла
        if photo_file.file_name:
            file_extension = Path(photo_file.file_name).suffix or ".jpg"
    
    if not photo_file:
        await message.reply_text("Не удалось получить изображение. Попробуйте отправить фото еще раз.")
        return
    
    try:
        # Показываем пользователю, что обрабатываем
        await message.reply_text("Обрабатываю изображение...")
        
        # Скачиваем файл
        tg_file = await bot.get_file(photo_file.file_id)
        
        # Формируем путь для сохранения
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_path = user_dir / f"image_{timestamp}{file_extension}"
        
        # Сохраняем файл
        await tg_file.download_to_drive(image_path)
        logger.info("Изображение сохранено: user_id=%s, path=%s", user_id, image_path)
        
        # Формируем промпт
        prompt = (
            "Вот фото с данными от пользователя. "
            "Необходимо из него вытащить данные о показателях здоровья согласно формату."
        )
        
        # Вызываем LLM для извлечения данных
        sleep_log = await extract_health_data(prompt, SleepLog, image_path=image_path)
        
        # Формируем ответ пользователю
        response = (
            "✅ Данные о сне извлечены из изображения:\n\n"
            f"📅 Дата: {sleep_log.date}\n"
            f"⏰ Время сна: {sleep_log.start} - {sleep_log.end}\n"
            f"⏱ Продолжительность: {sleep_log.duration}\n"
            f"⭐ Оценка качества: {sleep_log.score}/100\n"
            f"😴 Глубокий сон: {sleep_log.deep_stage}%\n"
            f"💤 Легкий сон: {sleep_log.light_stage}%\n"
            f"🌙 REM-фаза: {sleep_log.rem_stage}%\n"
            f"🔄 Пробуждений: {sleep_log.wake_up_count}\n"
            f"💨 Качество дыхания: {sleep_log.breathe_quality}/100\n"
            f"❤️ Средний пульс: {sleep_log.average_pulse} уд/мин\n"
            f"📊 Вариабельность пульса: {sleep_log.average_pulse_variability} мс\n"
            f"🫁 SpO2: {sleep_log.average_spo2}%\n"
            f"🌬 Частота дыхания: {sleep_log.breathe_frequency} вдохов/мин"
        )
        
        await message.reply_text(response)
        logger.info("Данные успешно извлечены и отправлены: user_id=%s", user_id)
        
    except Exception as e:
        logger.error("Ошибка при обработке изображения: user_id=%s, error=%s", user_id, e, exc_info=True)
        await message.reply_text(
            "Извините, произошла ошибка при обработке изображения. "
            "Попробуйте отправить фото еще раз или опишите данные текстом."
        )


async def process_text_stub(
    update: Update, context: ContextTypes.DEFAULT_TYPE, text: str
) -> None:
    # TODO: replace with real text pipeline
    await update.effective_message.reply_text("Ок, текст получен. (заглушка обработчика)")


async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "Главное меню:",
        reply_markup=build_main_menu_keyboard(),
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    user_dir = _ensure_user_data_dir(user.id)
    await post_start_hook_stub(update, context, user_dir)

    await update.effective_message.reply_text(
        f"Привет, {user.first_name}!\n\n"
        "Я HealthCompanion. Можешь отправлять текст и изображения.",
        parse_mode=ParseMode.HTML,
    )
    await send_main_menu(update, context)
    return MAIN_MENU


async def on_menu_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if not query:
        return MAIN_MENU

    await query.answer()
    action = query.data or ""

    print(f"action: {action}")

    if action == MenuAction.HISTORY:
        await query.message.reply_text("История данных: (заглушка)")
        return MAIN_MENU

    if action == MenuAction.ANALYSIS:
        await query.message.reply_text("Анализ: (заглушка)")
        return MAIN_MENU

    if action == MenuAction.MAIN:
        await send_main_menu(update, context)
        return MAIN_MENU

    await query.message.reply_text("Неизвестная команда меню.")
    return MAIN_MENU


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


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await process_image_stub(update, context)
    return MAIN_MENU


async def on_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.effective_message
    document = getattr(message, "document", None)
    if not document:
        return MAIN_MENU

    if not _document_looks_like_image(document.mime_type, document.file_name):
        await message.reply_text("Пожалуйста, отправь файл-изображение (png/jpg/webp/...).")
        return MAIN_MENU

    await process_image_stub(update, context)
    return MAIN_MENU


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.effective_message.text or "").strip()
    await process_text_stub(update, context, text)
    return MAIN_MENU


async def on_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text("Не понял. Отправь текст или изображение.")
    return MAIN_MENU


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text("Ок. Чтобы начать заново: /start")
    return ConversationHandler.END


async def prompt_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text("Нажми /start чтобы открыть главное меню.")


async def on_orphan_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    await query.answer()
    await query.message.reply_text("Нажми /start чтобы открыть главное меню.")
