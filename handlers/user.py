from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import ATM_TEXT
from database import repository
from keyboards.inline import (
    back_to_menu_keyboard,
    contest_not_participating_keyboard,
    contest_participating_keyboard,
    main_menu_keyboard,
    participate_confirm_keyboard,
    public_stats_keyboard,
    top_list_keyboard,
)
from utils.formatters import (
    format_personal_stats,
    format_public_stats,
    format_top_participants,
    format_top_winners,
    format_winner,
    stats_bar,
)
from utils.logger import get_logger
from utils.time_utils import time_ago

logger = get_logger(__name__)
router = Router()

_MENU_TEXT = "Выбери действие:"


# ─── /start (with optional deep-link payload) ─────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession) -> None:
    await repository.get_or_create_user(
        session, message.from_user.id, message.from_user.username
    )
    args = message.text.split(maxsplit=1)
    payload = args[1] if len(args) > 1 else ""

    # Deep-link from group button: /start contest_<id>
    if payload.startswith("contest_"):
        await _show_contest_screen(message, session, edit=False)
        return

    await message.answer(_MENU_TEXT, reply_markup=main_menu_keyboard())


# ─── Menu ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu")
async def cb_menu(call: CallbackQuery) -> None:
    await call.message.edit_text(_MENU_TEXT, reply_markup=main_menu_keyboard())
    await call.answer()


# ─── ⚡️ Розыгрыш ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "raffle")
async def cb_raffle(call: CallbackQuery, session: AsyncSession) -> None:
    await _show_contest_screen(call, session, edit=True)


# ─── 🔥 Участвовать (from main menu → same screen) ────────────────────────────

@router.callback_query(F.data == "participate")
async def cb_participate_menu(call: CallbackQuery, session: AsyncSession) -> None:
    await _show_contest_screen(call, session, edit=True)


# ─── Contest screen helper ────────────────────────────────────────────────────

async def _show_contest_screen(
    event: Message | CallbackQuery,
    session: AsyncSession,
    edit: bool,
) -> None:
    is_call = isinstance(event, CallbackQuery)
    user_id = event.from_user.id
    msg = event.message if is_call else event

    user = await repository.get_or_create_user(session, user_id, event.from_user.username)

    contest = await repository.get_active_contest(session)
    if not contest:
        text = "⚡️ <b>РОЗЫГРЫШ</b>\n\nСейчас нет активного конкурса.\nСледите за обновлениями!"
        kb = back_to_menu_keyboard()
        if edit:
            await msg.edit_text(text, parse_mode="HTML", reply_markup=kb)
        else:
            await msg.answer(text, parse_mode="HTML", reply_markup=kb)
        if is_call:
            await event.answer()
        return

    count = await repository.get_participant_count(session, contest.id)
    already = await repository.is_participant(session, contest.id, user_id)
    bar = stats_bar(time_ago(contest.created_at), count, contest.winners_count, contest.prize_text)

    if already:
        status_line = "👉 Вы участвуете в конкурсе, удачи 🤞🏻"
        kb = contest_participating_keyboard()
    else:
        if user.is_banned:
            status_line = "❌ Вы заблокированы"
            kb = back_to_menu_keyboard()
        else:
            status_line = "❌ Вы не участвуете"
            kb = contest_not_participating_keyboard()

    text = (
        f"🔥 <b>#{contest.id} ТЕКУЩИЙ КОНКУРС</b>\n\n"
        f"📌 {contest.title}\n\n"
        f"{bar}\n\n"
        f"{status_line}"
    )

    if edit:
        await msg.edit_text(text, parse_mode="HTML", reply_markup=kb)
    else:
        await msg.answer(text, parse_mode="HTML", reply_markup=kb)

    if is_call:
        await event.answer()


# ─── 🔥 Участвовать (button on contest screen) → confirm screen ───────────────

@router.callback_query(F.data == "contest_participate")
async def cb_contest_participate(call: CallbackQuery, session: AsyncSession) -> None:
    user = await repository.get_or_create_user(session, call.from_user.id, call.from_user.username)

    if user.is_banned:
        logger.warning("Banned participation attempt | telegram_id=%s", call.from_user.id)
        await call.answer("🚫 Вы заблокированы и не можете участвовать.", show_alert=True)
        return

    contest = await repository.get_active_contest(session)
    if not contest:
        await call.answer("⚡️ Конкурс уже завершён.", show_alert=True)
        return

    already = await repository.is_participant(session, contest.id, call.from_user.id)
    if already:
        logger.debug("Duplicate attempt | telegram_id=%s | contest_id=%s", call.from_user.id, contest.id)
        await call.answer("👉 Вы уже участвуете!", show_alert=True)
        return

    count = await repository.get_participant_count(session, contest.id)
    bar = stats_bar(time_ago(contest.created_at), count, contest.winners_count, contest.prize_text)

    await call.message.edit_text(
        f"📌 {contest.title}\n\n"
        f"{bar}\n\n"
        "Принять участие?",
        parse_mode="HTML",
        reply_markup=participate_confirm_keyboard(contest.id),
    )
    await call.answer()


# ─── ✅ Подтвердить участие ────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("confirm_participate:"))
async def cb_confirm_participate(call: CallbackQuery, session: AsyncSession) -> None:
    contest_id = int(call.data.split(":")[1])

    # Re-check ban (no cache — this is the write point)
    user = await repository.get_or_create_user(session, call.from_user.id, call.from_user.username)
    if user.is_banned:
        await call.answer("🚫 Вы заблокированы.", show_alert=True)
        return

    contest = await repository.get_active_contest(session)
    if not contest or contest.id != contest_id:
        await call.message.edit_text(
            "⚡️ Конкурс завершён или изменился.",
            reply_markup=back_to_menu_keyboard(),
        )
        await call.answer()
        return

    # Double-submit guard
    if await repository.is_participant(session, contest.id, call.from_user.id):
        await call.answer("👉 Вы уже участвуете!", show_alert=True)
        return

    await repository.add_participant(session, contest.id, call.from_user.id)
    count = await repository.get_participant_count(session, contest.id)
    bar = stats_bar(time_ago(contest.created_at), count, contest.winners_count, contest.prize_text)

    await call.message.edit_text(
        f"✅ <b>Вы зарегистрированы!</b>\n\n"
        f"📌 {contest.title}\n\n"
        f"{bar}\n\n"
        "👉 Ожидайте результатов. Удачи! 🤞🏻",
        parse_mode="HTML",
        reply_markup=back_to_menu_keyboard(),
    )
    await call.answer("✅ Вы участвуете!")


# ─── 📱 Моя статистика ────────────────────────────────────────────────────────

@router.callback_query(F.data == "my_stats")
async def cb_my_stats(call: CallbackQuery, session: AsyncSession) -> None:
    stats = await repository.get_user_stats(session, call.from_user.id)
    await call.message.edit_text(
        format_personal_stats(stats),
        parse_mode="HTML",
        reply_markup=back_to_menu_keyboard(),
    )
    await call.answer()


# ─── 🌍 Общая статистика ──────────────────────────────────────────────────────

@router.callback_query(F.data == "public_stats")
async def cb_public_stats(call: CallbackQuery, session: AsyncSession) -> None:
    stats = await repository.get_public_stats(session)
    await call.message.edit_text(
        format_public_stats(stats),
        parse_mode="HTML",
        reply_markup=public_stats_keyboard(),
    )
    await call.answer()


@router.callback_query(F.data == "top_winners")
async def cb_top_winners(call: CallbackQuery, session: AsyncSession) -> None:
    rows = await repository.get_top_winners(session)
    await call.message.edit_text(
        format_top_winners(rows),
        parse_mode="HTML",
        reply_markup=top_list_keyboard(),
    )
    await call.answer()


@router.callback_query(F.data == "top_participants")
async def cb_top_participants(call: CallbackQuery, session: AsyncSession) -> None:
    rows = await repository.get_top_participants(session)
    await call.message.edit_text(
        format_top_participants(rows),
        parse_mode="HTML",
        reply_markup=top_list_keyboard(),
    )
    await call.answer()


# ─── 🧲 ATM ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "atm")
async def cb_atm(call: CallbackQuery) -> None:
    await call.message.edit_text(
        f"🧲 <b>АТМ «МАГНИТ»</b>\n\n"
        f"📌 {ATM_TEXT}",
        parse_mode="HTML",
        reply_markup=back_to_menu_keyboard(),
    )
    await call.answer()
