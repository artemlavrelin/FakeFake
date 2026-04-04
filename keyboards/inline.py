from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ─── Main menu ────────────────────────────────────────────────────────────────

def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⚡️ Розыгрыш", callback_data="raffle"))
    builder.row(InlineKeyboardButton(text="🔥 Участвовать", callback_data="participate"))
    builder.row(
        InlineKeyboardButton(text="📱 Моя статистика", callback_data="my_stats"),
        InlineKeyboardButton(text="🌍 Общая статистика", callback_data="public_stats"),
    )
    builder.row(InlineKeyboardButton(text="🧲 ATM", callback_data="atm"))
    return builder.as_markup()


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="↩️ Назад", callback_data="menu"))
    return builder.as_markup()


# ─── Contest screens ──────────────────────────────────────────────────────────

def contest_not_participating_keyboard() -> InlineKeyboardMarkup:
    """Current contest screen — user is NOT participating."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔥 Участвовать", callback_data="contest_participate"))
    builder.row(InlineKeyboardButton(text="↩️ Назад", callback_data="menu"))
    return builder.as_markup()


def contest_participating_keyboard() -> InlineKeyboardMarkup:
    """Current contest screen — user IS already participating."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="↩️ Назад", callback_data="menu"))
    return builder.as_markup()


def participate_confirm_keyboard(contest_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_participate:{contest_id}"),
        InlineKeyboardButton(text="↩️ Назад", callback_data="raffle"),
    )
    return builder.as_markup()


# ─── Stats screens ────────────────────────────────────────────────────────────

def public_stats_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏆 Топ победителей", callback_data="top_winners"),
        InlineKeyboardButton(text="👥 Топ участников", callback_data="top_participants"),
    )
    builder.row(InlineKeyboardButton(text="↩️ Назад", callback_data="menu"))
    return builder.as_markup()


def top_list_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="↩️ Назад", callback_data="public_stats"))
    return builder.as_markup()


# ─── FSM cancel ───────────────────────────────────────────────────────────────

def cancel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="↩️ Отмена", callback_data="cancel_fsm"))
    return builder.as_markup()


# ─── Admin panel ──────────────────────────────────────────────────────────────

def admin_panel_keyboard(has_active: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if not has_active:
        builder.row(InlineKeyboardButton(text="⚡️ Создать конкурс", callback_data="admin:create"))
    else:
        builder.row(
            InlineKeyboardButton(text="✏️ Редактировать", callback_data="admin:edit"),
            InlineKeyboardButton(text="🚫 Отменить", callback_data="admin:cancel_contest"),
        )
        builder.row(InlineKeyboardButton(text="🎲 Провести розыгрыш", callback_data="admin:draw"))
    builder.row(InlineKeyboardButton(text="📣 Рассылка", callback_data="admin:broadcast"))
    builder.row(InlineKeyboardButton(text="👥 Пользователи", callback_data="admin:users"))
    return builder.as_markup()


def edit_contest_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📌 Описание", callback_data="edit:title"))
    builder.row(
        InlineKeyboardButton(text="💰 Приз (текст)", callback_data="edit:prize_text"),
        InlineKeyboardButton(text="💵 Сумма приза", callback_data="edit:prize_amount"),
    )
    builder.row(InlineKeyboardButton(text="🏆 Победителей", callback_data="edit:winners_count"))
    builder.row(InlineKeyboardButton(text="↩️ Назад", callback_data="admin:panel"))
    return builder.as_markup()


def cancel_contest_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да, отменить", callback_data="admin:cancel_contest_yes"),
        InlineKeyboardButton(text="↩️ Нет", callback_data="admin:panel"),
    )
    return builder.as_markup()


def broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Отправить", callback_data="broadcast:send"),
        InlineKeyboardButton(text="↩️ Отмена", callback_data="cancel_fsm"),
    )
    return builder.as_markup()


# ─── Group message ────────────────────────────────────────────────────────────

def group_contest_keyboard(bot_username: str, contest_id: int) -> InlineKeyboardMarkup:
    """Deep link button for group announcement."""
    url = f"https://t.me/{bot_username}?start=contest_{contest_id}"
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔥 Участвовать", url=url))
    return builder.as_markup()
