from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

# ─── User keyboard ─────────────────────────────────────────────────────────────

def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎯 Участвовать")],
            [KeyboardButton(text="🏆 Текущий конкурс")],
            [KeyboardButton(text="📋 Результаты")],
        ],
        resize_keyboard=True,
        persistent=True,
    )


def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
    )
