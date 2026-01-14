from __future__ import annotations

from dataclasses import dataclass

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


@dataclass(frozen=True)
class MenuAction:
    ADD_RECORD: str = "menu:add_record"
    HISTORY: str = "menu:history"
    ANALYSIS: str = "menu:analysis"
    MAIN: str = "menu:main"


def build_main_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("Добавить запись", callback_data=MenuAction.ADD_RECORD),
        ],
        [
            InlineKeyboardButton("История данных", callback_data=MenuAction.HISTORY),
            InlineKeyboardButton("Анализ", callback_data=MenuAction.ANALYSIS),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
