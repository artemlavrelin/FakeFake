from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🎯 Участвовать", callback_data="participate"))
    builder.row(InlineKeyboardButton(text="🏆 Текущий конкурс", callback_data="current_contest"))
    builder.row(InlineKeyboardButton(text="📋 Результаты", callback_data="results"))
    builder.row(InlineKeyboardButton(text="📊 Моя статистика", callback_data="my_stats"))
    return builder.as_markup()


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu"))
    return builder.as_markup()


def cancel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_create"))
    return builder.as_markup()


def participate_confirm_keyboard(contest_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_participate:{contest_id}"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="menu"),
    )
    return builder.as_markup()
