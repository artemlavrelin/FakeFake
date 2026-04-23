from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from strings import t


# ─── Language picker ──────────────────────────────────────────────────────────

def lang_keyboard() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang:ru"),
        InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang:en"),
    )
    return b.as_markup()


# ─── Main menu ────────────────────────────────────────────────────────────────

def main_menu_keyboard_v11(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="🫶 ПОЛУЧИТЬ ПРИЗ",  callback_data="loot"))
    b.row(InlineKeyboardButton(text="🤹🏼 РОЗЫГРЫШ",      callback_data="raffle"))
    b.row(InlineKeyboardButton(text="🥼 ПРОФИЛЬ",         callback_data="profile"))
    b.row(InlineKeyboardButton(text="🃏 ЗАДАНИЯ",          callback_data="tasks"))
    b.row(InlineKeyboardButton(text="⭐️ Выплаты / Отзывы / Статистика", callback_data="hub"))
    flag = "🇬🇧 to English" if lang == "ru" else "🇷🇺 на Русский"
    b.row(InlineKeyboardButton(text=f"💫 {flag}", callback_data="switch_lang"))
    return b.as_markup()


# Alias for backward compatibility
main_menu_keyboard = main_menu_keyboard_v11


def back_to_menu_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="menu"))
    return b.as_markup()


def cancel_keyboard(lang: str = "ru", back_cb: str = "cancel_fsm") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="⬅️ Отмена", callback_data=back_cb))
    return b.as_markup()


# ─── Raffle ───────────────────────────────────────────────────────────────────

def raffle_no_contest_keyboard(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="🔱 Топ победителей", callback_data="top_winners"),
        InlineKeyboardButton(text="⚜️ Топ участников",  callback_data="top_participants"),
    )
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="menu"))
    return b.as_markup()


def contest_not_participating_keyboard(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="⚡️ Участвовать", callback_data="contest_participate"))
    b.row(InlineKeyboardButton(text="⬅️ Назад",       callback_data="menu"))
    return b.as_markup()


def contest_participating_keyboard(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="menu"))
    return b.as_markup()


def participate_confirm_keyboard(lang: str, contest_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_participate:{contest_id}"),
        InlineKeyboardButton(text="⬅️ Назад",       callback_data="raffle"),
    )
    return b.as_markup()


# ─── Hub: Выплаты / Отзывы / Статистика ──────────────────────────────────────

def hub_keyboard(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="⭐️ Выплаты / Отзывы",    callback_data="report"))
    b.row(InlineKeyboardButton(text="📊 Моя статистика",        callback_data="my_stats_full"))
    b.row(InlineKeyboardButton(text="👥 Общая статистика",      callback_data="public_stats"))
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="menu"))
    return b.as_markup()


# ─── Report ───────────────────────────────────────────────────────────────────

def report_keyboard(lang: str, channel_url: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="➡️ Перейти",         url=channel_url))
    b.row(InlineKeyboardButton(text="✍️ Оставить отзыв",  callback_data="review:start"))
    b.row(InlineKeyboardButton(text="⬅️ Назад",           callback_data="hub"))
    return b.as_markup()


# ─── Stats ────────────────────────────────────────────────────────────────────

def public_stats_keyboard(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="🔱 Топ победителей", callback_data="top_winners"),
        InlineKeyboardButton(text="⚜️ Топ участников",  callback_data="top_participants"),
    )
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="hub"))
    return b.as_markup()


def top_list_keyboard(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="public_stats"))
    return b.as_markup()


def my_stats_keyboard(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="🌟 Вывод",   callback_data="withdraw"))
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="hub"))
    return b.as_markup()


# ─── Profile ──────────────────────────────────────────────────────────────────

def profile_keyboard(has_social: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if not has_social:
        b.row(InlineKeyboardButton(text="🧑🏻‍💻 Заполнить профиль", callback_data="profile:fill"))
    b.row(InlineKeyboardButton(text="🏁 Статистика", callback_data="my_stats_full"))
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="menu"))
    return b.as_markup()


# ─── Получить приз (ATM / Loot) ───────────────────────────────────────────────

def loot_entry_keyboard(lang: str, stake_url: str, binance_url: str) -> InlineKeyboardMarkup:
    """Entry screen when user has no payment data."""
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="🟨 Binance",  url=binance_url),
        InlineKeyboardButton(text="♠️ Stake",    url=stake_url),
    )
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="menu"))
    return b.as_markup()


def loot_start_keyboard(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="🎁 Loot / Получить", callback_data="loot:start"))
    b.row(InlineKeyboardButton(text="⬅️ Назад",            callback_data="menu"))
    return b.as_markup()


def loot_roll_keyboard(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="🎁 Loot", callback_data="loot:roll"))
    return b.as_markup()


# ─── Stake ────────────────────────────────────────────────────────────────────

def stake_no_data_keyboard(lang: str, stake_url: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="🔗 Регистрация",        url=stake_url))
    b.row(InlineKeyboardButton(text="✅ Добавить username",  callback_data="stake:add"))
    b.row(InlineKeyboardButton(text="⬅️ Назад",              callback_data="menu"))
    return b.as_markup()


def stake_has_data_keyboard(lang: str, stake_url: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="🔗 Регистрация",   url=stake_url))
    b.row(
        InlineKeyboardButton(text="✏️ Изменить", callback_data="stake:edit"),
        InlineKeyboardButton(text="🗑 Удалить",  callback_data="stake:delete"),
    )
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="menu"))
    return b.as_markup()


def stake_delete_confirm_keyboard(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✅ Да, удалить", callback_data="stake:delete_confirm"),
        InlineKeyboardButton(text="⬅️ Нет",         callback_data="atm:stake"),
    )
    return b.as_markup()


def stake_replace_confirm_keyboard(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✅ Да, заменить", callback_data="stake:replace_confirm"),
        InlineKeyboardButton(text="⬅️ Отмена",       callback_data="atm:stake"),
    )
    return b.as_markup()


# ─── Binance ──────────────────────────────────────────────────────────────────

def binance_no_data_keyboard(lang: str, binance_url: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="🔗 Регистрация",       url=binance_url))
    b.row(InlineKeyboardButton(text="✅ Добавить Binance ID", callback_data="binance:add"))
    b.row(InlineKeyboardButton(text="⬅️ Назад",              callback_data="menu"))
    return b.as_markup()


def binance_has_data_keyboard(lang: str, binance_url: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="🔗 Регистрация",   url=binance_url))
    b.row(
        InlineKeyboardButton(text="✏️ Изменить", callback_data="binance:edit"),
        InlineKeyboardButton(text="🗑 Удалить",  callback_data="binance:delete"),
    )
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="menu"))
    return b.as_markup()


def binance_delete_confirm_keyboard(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✅ Да, удалить", callback_data="binance:delete_confirm"),
        InlineKeyboardButton(text="⬅️ Нет",         callback_data="atm:binance"),
    )
    return b.as_markup()


def binance_replace_confirm_keyboard(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✅ Да, заменить", callback_data="binance:replace_confirm"),
        InlineKeyboardButton(text="⬅️ Отмена",       callback_data="atm:binance"),
    )
    return b.as_markup()


# ─── Tasks ────────────────────────────────────────────────────────────────────

def tasks_menu_keyboard() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="🟢 Принимать задания", callback_data="tasks:get"))
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="menu"))
    return b.as_markup()


# ─── Admin panel ──────────────────────────────────────────────────────────────

def admin_panel_keyboard(has_active: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if not has_active:
        b.row(InlineKeyboardButton(text="⚡️ Создать конкурс", callback_data="admin:create"))
    else:
        b.row(
            InlineKeyboardButton(text="✏️ Редактировать", callback_data="admin:edit"),
            InlineKeyboardButton(text="🚫 Отменить",       callback_data="admin:cancel_contest"),
        )
        b.row(InlineKeyboardButton(text="🎲 Провести розыгрыш", callback_data="admin:draw"))
    b.row(
        InlineKeyboardButton(text="📣 Рассылка",       callback_data="admin:broadcast"),
        InlineKeyboardButton(text="👥 Пользователи",   callback_data="admin:users"),
    )
    b.row(InlineKeyboardButton(text="💳 Платёж. данные", callback_data="admin:payments"))
    b.row(InlineKeyboardButton(text="⬅️ В меню", callback_data="menu"))
    return b.as_markup()


def edit_contest_keyboard() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="📌 Описание",    callback_data="edit:title"))
    b.row(
        InlineKeyboardButton(text="💰 Приз (текст)", callback_data="edit:prize_text"),
        InlineKeyboardButton(text="💵 Сумма",         callback_data="edit:prize_amount"),
    )
    b.row(InlineKeyboardButton(text="🏆 Победителей",  callback_data="edit:winners_count"))
    b.row(InlineKeyboardButton(text="⬅️ Назад",        callback_data="admin:panel"))
    return b.as_markup()


def cancel_contest_confirm_keyboard() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✅ Да, отменить", callback_data="admin:cancel_contest_yes"),
        InlineKeyboardButton(text="⬅️ Нет",          callback_data="admin:panel"),
    )
    return b.as_markup()


def broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✅ Отправить", callback_data="broadcast:send"),
        InlineKeyboardButton(text="⬅️ Отмена",   callback_data="cancel_fsm"),
    )
    return b.as_markup()


def payments_page_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"payments:page:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"payments:page:{page + 1}"))
    if nav:
        b.row(*nav)
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:panel"))
    return b.as_markup()


# ─── Group ────────────────────────────────────────────────────────────────────

def group_contest_keyboard(bot_link: str, contest_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="🧲 Участвовать",  callback_data=f"group_join:{contest_id}"),
        InlineKeyboardButton(text="🤖 Открыть бота", url=bot_link),
    )
    return b.as_markup()


def group_draw_keyboard(bot_link: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="🤖 Открыть бота", url=bot_link))
    return b.as_markup()


# ─── Social ───────────────────────────────────────────────────────────────────

def social_keyboard(fb: str, tw: str, ig: str, th: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="Facebook",  url=fb),
        InlineKeyboardButton(text="Twitter",   url=tw),
    )
    b.row(
        InlineKeyboardButton(text="Instagram", url=ig),
        InlineKeyboardButton(text="Threads",   url=th),
    )
    return b.as_markup()
