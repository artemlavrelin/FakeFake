import asyncio

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import ADMIN_IDS
from database import repository
from keyboards import cancel_keyboard, main_menu_keyboard
from states.contest import CreateContest
from utils.formatters import format_winner
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ─── /create_contest ──────────────────────────────────────────────────────────

@router.message(Command("create_contest"))
async def cmd_create_contest(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав администратора.")
        return

    # Rule: only 1 active contest at a time
    existing = await repository.get_active_contest(session)
    if existing:
        logger.warning(
            "Admin tried to create contest while one is active | admin=%s | active_contest_id=%s",
            message.from_user.id, existing.id,
        )
        await message.answer(
            f"⚠️ <b>Уже есть активный конкурс:</b> «{existing.title}»\n\n"
            "Сначала завершите его командой /draw.",
            parse_mode="HTML",
        )
        return

    await state.set_state(CreateContest.waiting_title)
    await message.answer(
        "📝 <b>Создание нового конкурса</b>\n\n"
        "Шаг 1/3 — Введите <b>название</b> конкурса:",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )


@router.callback_query(F.data == "cancel_create")
async def cb_cancel_create(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text("❌ Создание конкурса отменено.")
    await call.answer()


@router.message(CreateContest.waiting_title)
async def process_title(message: Message, state: FSMContext) -> None:
    if not message.text or len(message.text.strip()) < 3:
        await message.answer("⚠️ Название слишком короткое. Минимум 3 символа:")
        return
    await state.update_data(title=message.text.strip())
    await state.set_state(CreateContest.waiting_prize)
    await message.answer(
        "Шаг 2/3 — Введите <b>описание приза</b>:",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )


@router.message(CreateContest.waiting_prize)
async def process_prize(message: Message, state: FSMContext) -> None:
    if not message.text or len(message.text.strip()) < 3:
        await message.answer("⚠️ Описание слишком короткое. Попробуйте ещё раз:")
        return
    await state.update_data(prize_text=message.text.strip())
    await state.set_state(CreateContest.waiting_winners_count)
    await message.answer(
        "Шаг 3/3 — Введите <b>количество победителей</b> (1–100):",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )


@router.message(CreateContest.waiting_winners_count)
async def process_winners_count(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    if not message.text or not message.text.strip().isdigit():
        await message.answer("⚠️ Введите корректное число (например: 1, 3, 5):")
        return
    count = int(message.text.strip())
    if not (1 <= count <= 100):
        await message.answer("⚠️ Количество победителей должно быть от 1 до 100:")
        return

    data = await state.get_data()
    await state.clear()

    contest = await repository.create_contest(
        session,
        title=data["title"],
        prize_text=data["prize_text"],
        winners_count=count,
    )

    await message.answer(
        f"✅ <b>Конкурс создан!</b>\n\n"
        f"🆔 ID: <code>{contest.id}</code>\n"
        f"📌 Название: <b>{contest.title}</b>\n"
        f"🎁 Приз: {contest.prize_text}\n"
        f"🥇 Победителей: <b>{contest.winners_count}</b>\n\n"
        "Пользователи могут регистрироваться.",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )


# ─── /draw ────────────────────────────────────────────────────────────────────

@router.message(Command("draw"))
async def cmd_draw(message: Message, session: AsyncSession, bot: Bot) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав администратора.")
        return

    contest = await repository.get_active_contest(session)
    if not contest:
        await message.answer("😔 Нет активного конкурса для розыгрыша.")
        return

    participant_count = await repository.get_participant_count(session, contest.id)

    # Fail-safe: no participants
    if participant_count == 0:
        logger.warning("Draw aborted — no participants | contest_id=%s", contest.id)
        await message.answer(
            f"⚠️ В конкурсе <b>«{contest.title}»</b> нет участников.\n"
            "Розыгрыш невозможен.",
            parse_mode="HTML",
        )
        return

    # Fail-safe warning: fewer participants than requested winners
    if participant_count < contest.winners_count:
        await message.answer(
            f"⚠️ <b>Внимание:</b> участников (<b>{participant_count}</b>) меньше, "
            f"чем запланировано победителей (<b>{contest.winners_count}</b>).\n"
            f"Победителями станут все <b>{participant_count}</b> участников.",
            parse_mode="HTML",
        )

    await message.answer("🎲 Провожу розыгрыш...")

    # draw_winners handles fail-safe internally and returns (winners, participant_count)
    winners, total_participants = await repository.draw_winners(session, contest)

    finished = contest.finished_at.strftime("%d.%m.%Y %H:%M") if contest.finished_at else "—"
    winner_ids = {w.telegram_id for w in winners}

    winners_lines = [
        format_winner(w.telegram_id, w.user.username if w.user else None, i + 1)
        for i, w in enumerate(winners)
    ]
    winners_block = "\n".join(winners_lines)

    result_text = (
        f"🎊 <b>Розыгрыш завершён!</b>\n\n"
        f"🆔 Конкурс ID: <code>{contest.id}</code>\n"
        f"📌 Название: <b>{contest.title}</b>\n"
        f"🎁 Приз: {contest.prize_text}\n"
        f"👥 Участников: <b>{total_participants}</b>\n"
        f"📅 Дата: {finished}\n\n"
        f"🥇 <b>Победители ({len(winners)}):</b>\n{winners_block}"
    )

    await message.answer(result_text, parse_mode="HTML")

    # Notify all participants
    all_participants = await repository.get_all_participants(session, contest.id)
    await _notify_participants(
        bot=bot,
        participant_ids=[p.telegram_id for p in all_participants],
        winner_ids=winner_ids,
        contest_title=contest.title,
        prize_text=contest.prize_text,
        winners_lines=winners_lines,
    )


async def _notify_participants(
    bot: Bot,
    participant_ids: list[int],
    winner_ids: set[int],
    contest_title: str,
    prize_text: str,
    winners_lines: list[str],
) -> None:
    winners_block = "\n".join(winners_lines)

    winner_msg = (
        f"🎉 <b>Поздравляем! Вы победили!</b>\n\n"
        f"📌 Конкурс: <b>{contest_title}</b>\n"
        f"🎁 Приз: {prize_text}\n\n"
        "Свяжитесь с администратором для получения приза."
    )
    participant_msg = (
        f"📋 <b>Конкурс завершён!</b>\n\n"
        f"📌 {contest_title}\n\n"
        f"🥇 <b>Победители:</b>\n{winners_block}\n\n"
        "Спасибо за участие! Следите за новыми конкурсами 🍀"
    )

    sent = failed = 0
    for tg_id in participant_ids:
        try:
            text = winner_msg if tg_id in winner_ids else participant_msg
            await bot.send_message(tg_id, text, parse_mode="HTML")
            sent += 1
        except Exception as e:
            logger.warning("Notification failed | telegram_id=%s | error=%s", tg_id, e)
            failed += 1
        await asyncio.sleep(0.05)  # ~20 msg/sec, safe under Telegram limits

    logger.info("Notifications sent | sent=%s | failed=%s", sent, failed)


# ─── /ban & /unban ────────────────────────────────────────────────────────────

@router.message(Command("ban"))
async def cmd_ban(message: Message, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав администратора.")
        return
    args = message.text.split()
    if len(args) < 2 or not args[1].lstrip("-").isdigit():
        await message.answer("📖 Использование: /ban <telegram_id>")
        return
    target_id = int(args[1])
    user = await repository.set_ban(session, target_id, banned=True)
    if not user:
        await message.answer(f"❓ Пользователь <code>{target_id}</code> не найден.", parse_mode="HTML")
    else:
        name = f"@{user.username}" if user.username else f"<code>{target_id}</code>"
        await message.answer(f"🚫 {name} заблокирован.", parse_mode="HTML")


@router.message(Command("unban"))
async def cmd_unban(message: Message, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав администратора.")
        return
    args = message.text.split()
    if len(args) < 2 or not args[1].lstrip("-").isdigit():
        await message.answer("📖 Использование: /unban <telegram_id>")
        return
    target_id = int(args[1])
    user = await repository.set_ban(session, target_id, banned=False)
    if not user:
        await message.answer(f"❓ Пользователь <code>{target_id}</code> не найден.", parse_mode="HTML")
    else:
        name = f"@{user.username}" if user.username else f"<code>{target_id}</code>"
        await message.answer(f"✅ {name} разблокирован.", parse_mode="HTML")


# ─── /list_users ──────────────────────────────────────────────────────────────

@router.message(Command("list_users"))
async def cmd_list_users(message: Message, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав администратора.")
        return
    users = await repository.list_users(session)
    if not users:
        await message.answer("👥 Пользователей пока нет.")
        return
    lines = [f"👥 <b>Пользователи ({len(users)}):</b>\n"]
    for u in users:
        name = f"@{u.username}" if u.username else "—"
        status = "🚫" if u.is_banned else "✅"
        lines.append(f"{status} <code>{u.telegram_id}</code> {name}")
    for i in range(0, len(lines), 50):
        await message.answer("\n".join(lines[i:i + 50]), parse_mode="HTML")
