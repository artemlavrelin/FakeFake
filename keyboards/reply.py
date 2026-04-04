# Reply keyboard is not used in v4 (all UI is inline).
# Kept for compatibility; main_keyboard() is only called from keyboards/__init__.py.

from aiogram.types import ReplyKeyboardRemove


def main_keyboard() -> ReplyKeyboardRemove:
    """Remove any lingering reply keyboard when switching to inline UI."""
    return ReplyKeyboardRemove()
