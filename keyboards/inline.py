from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ─── Main menu ────────────────────────────────────────────────────────────────

def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🤹🏻 Розыгрыш", callback_data="raffle"))
    builder.row(InlineKeyboardButton(text="⭐️ Отчет", callback_data="report"))
    builder.row(
        InlineKeyboardButton(text="👀 Моя статистика", callback_data="my_stats"),
        InlineKeyboardButton(text="👥 Общая статистика", callback_data="public_stats"),
    )
    builder.row(InlineKeyboardButton(text="🧲 АТМ", callback_data="atm"))
    return builder.as_markup()


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="menu"))
    return builder.as_markup()


# ─── Contest screens ──────────────────────────────────────────────────────────

def contest_not_participating_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔥 Участвовать", callback_data="contest_participate"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="menu"))
    return builder.as_markup()


def contest_participating_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="menu"))
    return builder.as_markup()


def participate_confirm_keyboard(contest_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_participate:{contest_id}"),
        InlineKeyboardButton(text="➡️ Назад", callback_data="raffle"),
    )
    return builder.as_markup()


# ─── Report screen ────────────────────────────────────────────────────────────

def report_keyboard(channel_url: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➡️ Перейти", url=channel_url))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="menu"))
    return builder.as_markup()


# ─── Stats screens ────────────────────────────────────────────────────────────

def public_stats_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏆 Топ победителей", callback_data="top_winners"),
        InlineKeyboardButton(text="👥 Топ участников", callback_data="top_participants"),
    )
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="menu"))
    return builder.as_markup()


def top_list_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="public_stats"))
    return builder.as_markup()


# ─── ATM ─────────────────────────────────────────────────────────────────────

def atm_keyboard(has_data: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    label = "✏️ Изменить данные" if has_data else "💾 Сохранить данные"
    builder.row(InlineKeyboardButton(text=label, callback_data="atm_input"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="menu"))
    return builder.as_markup()


def atm_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Сохранить", callback_data="atm_confirm"),
        InlineKeyboardButton(text="⬅️ Отмена", callback_data="atm"),
    )
    return builder.as_markup()


# ─── FSM cancel ───────────────────────────────────────────────────────────────

def cancel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ Отмена", callback_data="cancel_fsm"))
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
    builder.row(
        InlineKeyboardButton(text="🎁 Бонус-розыгрыш", callback_data="admin:bonus_draw"),
        InlineKeyboardButton(text="📣 Рассылка", callback_data="admin:broadcast"),
    )
    builder.row(
        InlineKeyboardButton(text="👥 Пользователи", callback_data="admin:users"),
        InlineKeyboardButton(text="💳 Платёж. данные", callback_data="admin:payments"),
    )
    return builder.as_markup()


def edit_contest_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📌 Описание", callback_data="edit:title"))
    builder.row(
        InlineKeyboardButton(text="💰 Приз (текст)", callback_data="edit:prize_text"),
        InlineKeyboardButton(text="💵 Сумма", callback_data="edit:prize_amount"),
    )
    builder.row(InlineKeyboardButton(text="🏆 Победителей", callback_data="edit:winners_count"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:panel"))
    return builder.as_markup()


def cancel_contest_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да, отменить", callback_data="admin:cancel_contest_yes"),
        InlineKeyboardButton(text="⬅️ Нет", callback_data="admin:panel"),
    )
    return builder.as_markup()


def broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Отправить", callback_data="broadcast:send"),
        InlineKeyboardButton(text="⬅️ Отмена", callback_data="cancel_fsm"),
    )
    return builder.as_markup()


def payments_page_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"payments:page:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"payments:page:{page + 1}"))
    if nav:
        builder.row(*nav)
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:panel"))
    return builder.as_markup()


# ─── Group message buttons ────────────────────────────────────────────────────

def group_contest_keyboard(bot_username: str, contest_id: int) -> InlineKeyboardMarkup:
    """
    Buttons in the group announcement:
    • 🧲 Участвовать  — inline callback (user must have started the bot first)
    • 🤖 Открыть бота — URL to open private chat
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🧲 Участвовать",
            callback_data=f"group_join:{contest_id}",
        ),
        InlineKeyboardButton(
            text="🤖 Открыть бота",
            url=f"https://t.me/{bot_username}",
        ),
    )
    return builder.as_markup()


def group_draw_keyboard(bot_username: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🤖 Открыть бота", url=f"https://t.me/{bot_username}"))
    return builder.as_markup()
