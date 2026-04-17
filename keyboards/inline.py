from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from i18n import t


# ─── Language picker ──────────────────────────────────────────────────────────

def lang_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang:ru"),
        InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang:en"),
    )
    return builder.as_markup()


# ─── Main menu ────────────────────────────────────────────────────────────────

def main_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=t(lang, "btn_raffle"),       callback_data="raffle"))
    builder.row(InlineKeyboardButton(text=t(lang, "btn_report"),       callback_data="report"))
    builder.row(
        InlineKeyboardButton(text=t(lang, "btn_my_stats"),    callback_data="my_stats"),
        InlineKeyboardButton(text=t(lang, "btn_public_stats"), callback_data="public_stats"),
    )
    builder.row(
        InlineKeyboardButton(text=t(lang, "btn_atm"),     callback_data="atm"),
        InlineKeyboardButton(text=t(lang, "btn_reviews"), callback_data="reviews"),
    )
    # Language switch
    flag = "🇬🇧 EN" if lang == "ru" else "🇷🇺 RU"
    builder.row(InlineKeyboardButton(text=flag, callback_data="switch_lang"))
    return builder.as_markup()


def back_to_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="menu"))
    return builder.as_markup()


# ─── Contest screens ──────────────────────────────────────────────────────────

def contest_not_participating_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=t(lang, "btn_participate"), callback_data="contest_participate"))
    builder.row(InlineKeyboardButton(text=t(lang, "btn_back"),        callback_data="menu"))
    return builder.as_markup()


def contest_participating_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="menu"))
    return builder.as_markup()


def participate_confirm_keyboard(lang: str, contest_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=t(lang, "btn_confirm"), callback_data=f"confirm_participate:{contest_id}"),
        InlineKeyboardButton(text=t(lang, "btn_back"),    callback_data="raffle"),
    )
    return builder.as_markup()


# ─── Report ───────────────────────────────────────────────────────────────────

def report_keyboard(lang: str, channel_url: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=t(lang, "btn_go"),   url=channel_url))
    builder.row(InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="menu"))
    return builder.as_markup()


# ─── Stats ────────────────────────────────────────────────────────────────────

def public_stats_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=t(lang, "btn_top_winners"),      callback_data="top_winners"),
        InlineKeyboardButton(text=t(lang, "btn_top_participants"), callback_data="top_participants"),
    )
    builder.row(InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="menu"))
    return builder.as_markup()


def top_list_keyboard(lang: str, back_cb: str = "public_stats") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=t(lang, "btn_back"), callback_data=back_cb))
    return builder.as_markup()


# ─── ATM hub ──────────────────────────────────────────────────────────────────

def atm_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=t(lang, "btn_stake"),   callback_data="atm:stake"),
        InlineKeyboardButton(text=t(lang, "btn_binance"), callback_data="atm:binance"),
    )
    builder.row(InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="menu"))
    return builder.as_markup()


# ─── Stake section ────────────────────────────────────────────────────────────

def stake_keyboard(lang: str, stake_url: str, has_data: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=t(lang, "btn_reg_stake"), url=stake_url))
    if has_data:
        builder.row(
            InlineKeyboardButton(text=t(lang, "btn_edit"),   callback_data="stake:edit"),
            InlineKeyboardButton(text=t(lang, "btn_delete"), callback_data="stake:delete"),
        )
    else:
        builder.row(InlineKeyboardButton(text=t(lang, "btn_edit"), callback_data="stake:edit"))
    builder.row(InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="atm"))
    return builder.as_markup()


def stake_delete_confirm_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=t(lang, "btn_yes_delete"), callback_data="stake:delete_confirm"),
        InlineKeyboardButton(text=t(lang, "btn_back"),       callback_data="atm:stake"),
    )
    return builder.as_markup()


# ─── Binance section ──────────────────────────────────────────────────────────

def binance_keyboard(lang: str, binance_url: str, has_data: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=t(lang, "btn_reg_binance"), url=binance_url))
    if has_data:
        builder.row(
            InlineKeyboardButton(text=t(lang, "btn_edit"),   callback_data="binance:edit"),
            InlineKeyboardButton(text=t(lang, "btn_delete"), callback_data="binance:delete"),
        )
    else:
        builder.row(InlineKeyboardButton(text=t(lang, "btn_edit"), callback_data="binance:edit"))
    builder.row(InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="atm"))
    return builder.as_markup()


def binance_delete_confirm_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=t(lang, "btn_yes_delete"), callback_data="binance:delete_confirm"),
        InlineKeyboardButton(text=t(lang, "btn_back"),       callback_data="atm:binance"),
    )
    return builder.as_markup()


# ─── Reviews ──────────────────────────────────────────────────────────────────

def reviews_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=t(lang, "btn_leave_review"), callback_data="review:start"))
    builder.row(InlineKeyboardButton(text=t(lang, "btn_back"),         callback_data="menu"))
    return builder.as_markup()


# ─── FSM cancel ───────────────────────────────────────────────────────────────

def cancel_keyboard(lang: str, back_cb: str = "cancel_fsm") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data=back_cb))
    return builder.as_markup()


# ─── Admin panel ──────────────────────────────────────────────────────────────

def admin_panel_keyboard(has_active: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if not has_active:
        builder.row(InlineKeyboardButton(text="⚡️ Создать конкурс", callback_data="admin:create"))
    else:
        builder.row(
            InlineKeyboardButton(text="✏️ Редактировать", callback_data="admin:edit"),
            InlineKeyboardButton(text="🚫 Отменить",       callback_data="admin:cancel_contest"),
        )
        builder.row(InlineKeyboardButton(text="🎲 Провести розыгрыш", callback_data="admin:draw"))
    builder.row(
        InlineKeyboardButton(text="📣 Рассылка",       callback_data="admin:broadcast"),
        InlineKeyboardButton(text="👥 Пользователи",   callback_data="admin:users"),
    )
    builder.row(InlineKeyboardButton(text="💳 Платёж. данные", callback_data="admin:payments"))
    builder.row(InlineKeyboardButton(text="⬅️ В меню",          callback_data="menu"))
    return builder.as_markup()


def edit_contest_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📌 Описание",       callback_data="edit:title"))
    builder.row(
        InlineKeyboardButton(text="💰 Приз (текст)", callback_data="edit:prize_text"),
        InlineKeyboardButton(text="💵 Сумма",         callback_data="edit:prize_amount"),
    )
    builder.row(InlineKeyboardButton(text="🏆 Победителей",     callback_data="edit:winners_count"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад",           callback_data="admin:panel"))
    return builder.as_markup()


def cancel_contest_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да, отменить", callback_data="admin:cancel_contest_yes"),
        InlineKeyboardButton(text="⬅️ Нет",          callback_data="admin:panel"),
    )
    return builder.as_markup()


def broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Отправить", callback_data="broadcast:send"),
        InlineKeyboardButton(text="⬅️ Отмена",   callback_data="cancel_fsm"),
    )
    return builder.as_markup()


def payments_page_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"payments:page:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"payments:page:{page + 1}"))
    if nav:
        builder.row(*nav)
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:panel"))
    return builder.as_markup()


# ─── Group buttons ────────────────────────────────────────────────────────────

def group_contest_keyboard(bot_link: str, contest_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🧲 Участвовать",  callback_data=f"group_join:{contest_id}"),
        InlineKeyboardButton(text="🤖 Открыть бота", url=bot_link),
    )
    return builder.as_markup()


def group_draw_keyboard(bot_link: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🤖 Открыть бота", url=bot_link))
    return builder.as_markup()
