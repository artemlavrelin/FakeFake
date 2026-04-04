from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database import repository
from keyboards import (
    back_to_menu_keyboard,
    main_menu_keyboard,
    participate_confirm_keyboard,
)
from utils.formatters import format_stats
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router()

WELCOME_TEXT = (
    "👋 Привет, <b>{name}</b>!\n\n"
    "Добро пожаловать в бот конкурсов.\n"
    "Используй кнопки ниже:"
)


# ─── /start ───────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession) -> None:
    await repository.get_or_create_user(
        session,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
    )
    await message.answer(
        WELCOME_TEXT.format(name=message.from_user.full_name),
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )


# ─── Main menu ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu")
async def cb_menu(call: CallbackQuery) -> None:
    await call.message.edit_text(
        WELCOME_TEXT.format(name=call.from_user.full_name),
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )
    await call.answer()


# ─── Участвовать (step 1) ─────────────────────────────────────────────────────

@router.callback_query(F.data == "participate")
async def cb_participate(call: CallbackQuery, session: AsyncSession) -> None:
    # Anti-abuse check 1: ban status
    user = await repository.get_or_create_user(session, call.from_user.id, call.from_user.username)
    if user.is_banned:
        logger.warning(
            "Banned user attempted to participate | telegram_id=%s", call.from_user.id
        )
        await call.answer("🚫 Вы заблокированы и не можете участвовать.", show_alert=True)
        return

    contest = await repository.get_active_contest(session)
    if not contest:
        await call.message.edit_text(
            "😔 <b>Нет активного конкурса</b>\n\nСледите за обновлениями!",
            parse_mode="HTML",
            reply_markup=back_to_menu_keyboard(),
        )
        await call.answer()
        return

    # Anti-abuse check 2: already participating
    already = await repository.is_participant(session, contest.id, call.from_user.id)
    if already:
        count = await repository.get_participant_count(session, contest.id)
        logger.debug(
            "Duplicate participation attempt ignored | telegram_id=%s | contest_id=%s",
            call.from_user.id, contest.id,
        )
        await call.message.edit_text(
            f"✅ <b>Вы уже в конкурсе!</b>\n\n"
            f"📌 {contest.title}\n"
            f"🎁 {contest.prize_text}\n"
            f"👥 Участников: <b>{count}</b>\n\n"
            "Ждите объявления победителей 🍀",
            parse_mode="HTML",
            reply_markup=back_to_menu_keyboard(),
        )
        await call.answer("✅ Вы уже участвуете!")
        return

    count = await repository.get_participant_count(session, contest.id)
    await call.message.edit_text(
        f"🎯 <b>Участие в конкурсе</b>\n\n"
        f"📌 Название: <b>{contest.title}</b>\n"
        f"🎁 Приз: {contest.prize_text}\n"
        f"🥇 Победителей: <b>{contest.winners_count}</b>\n"
        f"👥 Участников сейчас: <b>{count}</b>\n\n"
        "Подтверди участие:",
        parse_mode="HTML",
        reply_markup=participate_confirm_keyboard(contest.id),
    )
    await call.answer()


# ─── Участвовать (step 2: confirm) ────────────────────────────────────────────

@router.callback_query(F.data.startswith("confirm_participate:"))
async def cb_confirm_participate(call: CallbackQuery, session: AsyncSession) -> None:
    contest_id = int(call.data.split(":")[1])

    # Anti-abuse check 1: ban status (re-check after throttle window)
    user = await repository.get_or_create_user(session, call.from_user.id, call.from_user.username)
    if user.is_banned:
        logger.warning(
            "Banned user attempted confirm | telegram_id=%s", call.from_user.id
        )
        await call.answer("🚫 Вы заблокированы.", show_alert=True)
        return

    contest = await repository.get_active_contest(session)
    if not contest or contest.id != contest_id:
        await call.message.edit_text(
            "⚠️ Конкурс уже завершён или изменился.",
            reply_markup=back_to_menu_keyboard(),
        )
        await call.answer()
        return

    # Anti-abuse check 2: double-submit / callback spam guard
    already = await repository.is_participant(session, contest.id, call.from_user.id)
    if already:
        logger.debug(
            "Double-submit blocked | telegram_id=%s | contest_id=%s",
            call.from_user.id, contest.id,
        )
        await call.answer("✅ Вы уже участвуете!", show_alert=True)
        return

    await repository.add_participant(session, contest.id, call.from_user.id)
    count = await repository.get_participant_count(session, contest.id)

    await call.message.edit_text(
        f"🎉 <b>Вы успешно зарегистрированы!</b>\n\n"
        f"📌 {contest.title}\n"
        f"🎁 {contest.prize_text}\n"
        f"👥 Участников теперь: <b>{count}</b>\n\n"
        "Удачи! 🍀",
        parse_mode="HTML",
        reply_markup=back_to_menu_keyboard(),
    )
    await call.answer("🎉 Вы в конкурсе!")


# ─── Текущий конкурс ──────────────────────────────────────────────────────────

@router.callback_query(F.data == "current_contest")
async def cb_current_contest(call: CallbackQuery, session: AsyncSession) -> None:
    contest = await repository.get_active_contest(session)
    if not contest:
        await call.message.edit_text(
            "😔 <b>Нет активного конкурса</b>\n\nСледите за обновлениями!",
            parse_mode="HTML",
            reply_markup=back_to_menu_keyboard(),
        )
        await call.answer()
        return

    count = await repository.get_participant_count(session, contest.id)
    already = await repository.is_participant(session, contest.id, call.from_user.id)
    participation_note = "✅ <i>Вы участвуете</i>" if already else "➡️ <i>Нажмите «Участвовать» чтобы присоединиться</i>"

    await call.message.edit_text(
        f"🏆 <b>Активный конкурс</b>\n\n"
        f"📌 Название: <b>{contest.title}</b>\n"
        f"🎁 Приз: {contest.prize_text}\n"
        f"🥇 Победителей: <b>{contest.winners_count}</b>\n"
        f"👥 Участников: <b>{count}</b>\n\n"
        f"{participation_note}",
        parse_mode="HTML",
        reply_markup=back_to_menu_keyboard(),
    )
    await call.answer()


# ─── Результаты ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "results")
async def cb_results(call: CallbackQuery, session: AsyncSession) -> None:
    from utils.formatters import format_winner

    contests = await repository.get_finished_contests(session)
    if not contests:
        await call.message.edit_text(
            "📋 <b>Результатов пока нет</b>\n\nЗавершённые конкурсы появятся здесь.",
            parse_mode="HTML",
            reply_markup=back_to_menu_keyboard(),
        )
        await call.answer()
        return

    lines = ["📋 <b>Результаты последних конкурсов:</b>\n"]
    for c in contests:
        lines.append(f"🏆 <b>{c.title}</b>")
        lines.append(f"🎁 {c.prize_text}")
        if c.winners:
            winners_txt = ", ".join(
                format_winner(w.telegram_id, w.user.username if w.user else None, i + 1)
                for i, w in enumerate(c.winners)
            )
            lines.append(f"🥇 Победители: {winners_txt}")
        else:
            lines.append("🥇 Победители не определены")
        finished = c.finished_at.strftime("%d.%m.%Y %H:%M") if c.finished_at else "—"
        lines.append(f"📅 {finished}\n")

    await call.message.edit_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=back_to_menu_keyboard(),
    )
    await call.answer()


# ─── Моя статистика ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "my_stats")
async def cb_my_stats(call: CallbackQuery, session: AsyncSession) -> None:
    stats = await repository.get_user_stats(session, call.from_user.id)
    text = format_stats(
        participations=stats["participations"],
        wins=stats["wins"],
    )
    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=back_to_menu_keyboard(),
    )
    await call.answer()
