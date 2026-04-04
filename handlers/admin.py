import asyncio

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import ADMIN_IDS, BOT_USERNAME, GROUP_ID
from database import repository
from keyboards.inline import (
    admin_panel_keyboard,
    broadcast_confirm_keyboard,
    cancel_contest_confirm_keyboard,
    cancel_keyboard,
    edit_contest_keyboard,
    group_contest_keyboard,
    main_menu_keyboard,
)
from states.contest import Broadcast, CreateContest, EditContest
from utils.formatters import format_winner, stats_bar
from utils.logger import get_logger
from utils.time_utils import time_ago

logger = get_logger(__name__)
router = Router()

EDIT_FIELD_LABELS = {
    "title": "описание конкурса",
    "prize_text": "текст приза",
    "prize_amount": "сумму приза (число)",
    "winners_count": "количество победителей (число)",
}


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ─── /admin — панель ──────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return
    await _show_admin_panel(message, session, edit=False)


@router.callback_query(F.data == "admin:panel")
async def cb_admin_panel(call: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    await _show_admin_panel(call, session, edit=True)


async def _show_admin_panel(
    event: Message | CallbackQuery, session: AsyncSession, edit: bool
) -> None:
    contest = await repository.get_active_contest(session)
    has_active = contest is not None

    if has_active:
        count = await repository.get_participant_count(session, contest.id)
        bar = stats_bar(time_ago(contest.created_at), count, contest.winners_count, contest.prize_text)
        text = (
            f"🔧 <b>ПАНЕЛЬ АДМИНИСТРАТОРА</b>\n\n"
            f"🔥 Активный конкурс: <b>#{contest.id}</b>\n"
            f"📌 {contest.title}\n"
            f"{bar}"
        )
    else:
        text = "🔧 <b>ПАНЕЛЬ АДМИНИСТРАТОРА</b>\n\nАктивных конкурсов нет."

    kb = admin_panel_keyboard(has_active)
    msg = event.message if isinstance(event, CallbackQuery) else event
    if edit:
        await msg.edit_text(text, parse_mode="HTML", reply_markup=kb)
        await event.answer()
    else:
        await msg.answer(text, parse_mode="HTML", reply_markup=kb)


# ─── Создать конкурс ──────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:create")
async def cb_admin_create(call: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return

    existing = await repository.get_active_contest(session)
    if existing:
        await call.answer(f"⚠️ Уже есть активный конкурс #{existing.id}. Завершите его.", show_alert=True)
        return

    await state.set_state(CreateContest.waiting_title)
    await call.message.edit_text(
        "📝 <b>Создание конкурса — шаг 1/4</b>\n\n"
        "📌 Введите <b>описание конкурса</b> (текст, который увидят участники):",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )
    await call.answer()


@router.message(CreateContest.waiting_title)
async def process_title(message: Message, state: FSMContext) -> None:
    if not message.text or len(message.text.strip()) < 3:
        await message.answer("⚠️ Слишком короткое. Минимум 3 символа:")
        return
    await state.update_data(title=message.text.strip())
    await state.set_state(CreateContest.waiting_prize_text)
    await message.answer(
        "Шаг 2/4 — Введите <b>текст приза</b> (например: «10$ USDT»):",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )


@router.message(CreateContest.waiting_prize_text)
async def process_prize_text(message: Message, state: FSMContext) -> None:
    if not message.text or len(message.text.strip()) < 1:
        await message.answer("⚠️ Введите текст приза:")
        return
    await state.update_data(prize_text=message.text.strip())
    await state.set_state(CreateContest.waiting_prize_amount)
    await message.answer(
        "Шаг 3/4 — Введите <b>сумму приза числом</b> (используется в статистике).\n"
        "Если не нужно — введите <code>0</code>:",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )


@router.message(CreateContest.waiting_prize_amount)
async def process_prize_amount(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip().replace(",", ".")
    try:
        amount = float(text)
        if amount < 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Введите число (например: 10, 50.5 или 0):")
        return
    await state.update_data(prize_amount=amount)
    await state.set_state(CreateContest.waiting_winners_count)
    await message.answer(
        "Шаг 4/4 — Введите <b>количество победителей</b> (1–100):",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )


@router.message(CreateContest.waiting_winners_count)
async def process_winners_count(
    message: Message, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    text = (message.text or "").strip()
    if not text.isdigit() or not (1 <= int(text) <= 100):
        await message.answer("⚠️ Введите число от 1 до 100:")
        return

    data = await state.get_data()
    await state.clear()

    contest = await repository.create_contest(
        session,
        title=data["title"],
        prize_text=data["prize_text"],
        prize_amount=data["prize_amount"],
        winners_count=int(text),
    )

    await message.answer(
        f"✅ <b>Конкурс #{contest.id} создан!</b>\n\n"
        f"📌 {contest.title}\n"
        f"💰 {contest.prize_text}\n"
        f"🏆 Победителей: <b>{contest.winners_count}</b>",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )

    # Notify group
    await _notify_group_new_contest(bot, contest)


# ─── Редактировать конкурс ────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:edit")
async def cb_admin_edit(call: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True)
        return
    contest = await repository.get_active_contest(session)
    if not contest:
        await call.answer("Нет активного конкурса.", show_alert=True)
        return

    await state.set_state(EditContest.choosing_field)
    await state.update_data(contest_id=contest.id)
    await call.message.edit_text(
        f"✏️ <b>Редактирование конкурса #{contest.id}</b>\n\nЧто изменить?",
        parse_mode="HTML",
        reply_markup=edit_contest_keyboard(),
    )
    await call.answer()


@router.callback_query(F.data.startswith("edit:"))
async def cb_edit_field(call: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True)
        return

    field = call.data.split(":")[1]
    label = EDIT_FIELD_LABELS.get(field, field)
    await state.update_data(edit_field=field)
    await state.set_state(EditContest.waiting_value)
    await call.message.edit_text(
        f"✏️ Введите новое <b>{label}</b>:",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )
    await call.answer()


@router.message(EditContest.waiting_value)
async def process_edit_value(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    data = await state.get_data()
    field = data.get("edit_field", "")
    raw = (message.text or "").strip()

    # Validate numeric fields
    if field in ("prize_amount",):
        try:
            value = float(raw.replace(",", "."))
        except ValueError:
            await message.answer("⚠️ Введите число:")
            return
    elif field == "winners_count":
        if not raw.isdigit() or not (1 <= int(raw) <= 100):
            await message.answer("⚠️ Введите число от 1 до 100:")
            return
        value = int(raw)
    else:
        if len(raw) < 1:
            await message.answer("⚠️ Значение не может быть пустым:")
            return
        value = raw

    await state.clear()

    contest = await repository.get_active_contest(session)
    if not contest:
        await message.answer("⚠️ Активный конкурс не найден.")
        return

    await repository.edit_contest(session, contest, field, value)
    await message.answer(
        f"✅ <b>Конкурс #{contest.id} обновлён</b>\n"
        f"Поле «{EDIT_FIELD_LABELS.get(field, field)}» изменено.",
        parse_mode="HTML",
        reply_markup=admin_panel_keyboard(True),
    )


# ─── Отменить конкурс ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:cancel_contest")
async def cb_cancel_contest(call: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True)
        return
    contest = await repository.get_active_contest(session)
    if not contest:
        await call.answer("Нет активного конкурса.", show_alert=True)
        return

    await call.message.edit_text(
        f"🚫 <b>Отменить конкурс #{contest.id}?</b>\n\n"
        f"📌 {contest.title}\n\n"
        "Это действие необратимо.",
        parse_mode="HTML",
        reply_markup=cancel_contest_confirm_keyboard(),
    )
    await call.answer()


@router.callback_query(F.data == "admin:cancel_contest_yes")
async def cb_cancel_contest_yes(
    call: CallbackQuery, session: AsyncSession, bot: Bot
) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True)
        return
    contest = await repository.get_active_contest(session)
    if not contest:
        await call.answer("Нет активного конкурса.", show_alert=True)
        return

    await repository.cancel_contest(session, contest)
    await call.message.edit_text(
        f"🚫 Конкурс <b>#{contest.id} «{contest.title}»</b> отменён.",
        parse_mode="HTML",
        reply_markup=admin_panel_keyboard(False),
    )
    await call.answer("Конкурс отменён.")


# ─── Розыгрыш ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:draw")
async def cb_admin_draw(call: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True)
        return
    await _run_draw(call.message, session, bot, edit=True)
    await call.answer()


@router.message(Command("draw"))
async def cmd_draw(message: Message, session: AsyncSession, bot: Bot) -> None:
    if not is_admin(message.from_user.id):
        return
    await _run_draw(message, session, bot, edit=False)


async def _run_draw(
    msg: Message, session: AsyncSession, bot: Bot, edit: bool
) -> None:
    contest = await repository.get_active_contest(session)
    if not contest:
        text = "😔 Нет активного конкурса."
        if edit:
            await msg.edit_text(text)
        else:
            await msg.answer(text)
        return

    count = await repository.get_participant_count(session, contest.id)
    if count == 0:
        text = f"⚠️ В конкурсе <b>#{contest.id}</b> нет участников."
        if edit:
            await msg.edit_text(text, parse_mode="HTML", reply_markup=admin_panel_keyboard(True))
        else:
            await msg.answer(text, parse_mode="HTML")
        return

    if count < contest.winners_count:
        warn = (
            f"⚠️ Участников (<b>{count}</b>) меньше запланированного числа победителей "
            f"(<b>{contest.winners_count}</b>). Победителями станут все участники."
        )
        if edit:
            await msg.edit_text(warn, parse_mode="HTML")
        else:
            await msg.answer(warn, parse_mode="HTML")

    winners, total = await repository.draw_winners(session, contest)
    winner_ids = {w.telegram_id for w in winners}

    winners_lines = [
        format_winner(w.telegram_id, w.user.username if w.user else None, i + 1)
        for i, w in enumerate(winners)
    ]
    finished = contest.finished_at.strftime("%d.%m.%Y %H:%M") if contest.finished_at else "—"

    result_text = (
        f"🎊 <b>Розыгрыш завершён!</b>\n\n"
        f"⚡️ Конкурс: <b>#{contest.id}</b>\n"
        f"📌 {contest.title}\n"
        f"💰 {contest.prize_text}\n"
        f"👥 Участников: <b>{total}</b>\n"
        f"📅 {finished}\n\n"
        f"🏆 <b>Победители ({len(winners)}):</b>\n" + "\n".join(winners_lines)
    )

    if edit:
        await msg.edit_text(result_text, parse_mode="HTML", reply_markup=admin_panel_keyboard(False))
    else:
        await msg.answer(result_text, parse_mode="HTML")

    # Notify all participants
    all_participants = await repository.get_all_participants(session, contest.id)
    await _notify_participants(
        bot, [p.telegram_id for p in all_participants],
        winner_ids, contest.title, contest.prize_text, winners_lines,
    )

    # Update group message
    await _notify_group_draw(bot, contest.id, contest.title, winners_lines)


# ─── Рассылка ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:broadcast")
async def cb_admin_broadcast(call: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True)
        return
    await state.set_state(Broadcast.waiting_message)
    await call.message.edit_text(
        "📣 <b>Рассылка</b>\n\nВведите текст сообщения для всех пользователей:",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )
    await call.answer()


@router.message(Broadcast.waiting_message)
async def process_broadcast_message(message: Message, state: FSMContext, session: AsyncSession) -> None:
    user_ids = await repository.get_all_user_ids(session)
    await state.update_data(text=message.text, user_count=len(user_ids))
    await state.set_state(Broadcast.confirm)
    await message.answer(
        f"📣 <b>Предпросмотр рассылки</b>\n\n"
        f"──────────────\n{message.text}\n──────────────\n\n"
        f"👥 Получателей: <b>{len(user_ids)}</b>\n\nОтправить?",
        parse_mode="HTML",
        reply_markup=broadcast_confirm_keyboard(),
    )


@router.callback_query(F.data == "broadcast:send")
async def cb_broadcast_send(
    call: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True)
        return
    data = await state.get_data()
    text = data.get("text", "")
    await state.clear()

    user_ids = await repository.get_all_user_ids(session)
    await call.message.edit_text(
        f"📣 Рассылка запущена... ({len(user_ids)} пользователей)",
        parse_mode="HTML",
    )
    await call.answer()

    sent, failed = await _broadcast(bot, user_ids, text)
    await call.message.answer(
        f"✅ <b>Рассылка завершена</b>\n"
        f"📤 Отправлено: <b>{sent}</b>\n"
        f"❌ Ошибок: <b>{failed}</b>",
        parse_mode="HTML",
        reply_markup=admin_panel_keyboard(False),
    )


async def _broadcast(bot: Bot, user_ids: list[int], text: str) -> tuple[int, int]:
    sent = failed = 0
    for uid in user_ids:
        try:
            await bot.send_message(uid, text)
            sent += 1
        except Exception as e:
            logger.warning("Broadcast fail | telegram_id=%s | error=%s", uid, e)
            failed += 1
        await asyncio.sleep(0.05)
    logger.info("Broadcast done | sent=%s | failed=%s", sent, failed)
    return sent, failed


# ─── Уведомления ─────────────────────────────────────────────────────────────

async def _notify_participants(
    bot: Bot,
    participant_ids: list[int],
    winner_ids: set[int],
    contest_title: str,
    prize_text: str,
    winners_lines: list[str],
) -> None:
    block = "\n".join(winners_lines)
    winner_msg = (
        f"🎉 <b>Поздравляем — вы победили!</b>\n\n"
        f"📌 {contest_title}\n"
        f"💰 Приз: {prize_text}\n\n"
        "Свяжитесь с администратором для получения приза."
    )
    other_msg = (
        f"⚡️ <b>Конкурс завершён</b>\n\n"
        f"📌 {contest_title}\n\n"
        f"🏆 <b>Победители:</b>\n{block}\n\n"
        "Спасибо за участие! Следите за новыми конкурсами 🍀"
    )
    sent = failed = 0
    for uid in participant_ids:
        try:
            await bot.send_message(uid, winner_msg if uid in winner_ids else other_msg, parse_mode="HTML")
            sent += 1
        except Exception as e:
            logger.warning("Notify fail | telegram_id=%s | %s", uid, e)
            failed += 1
        await asyncio.sleep(0.05)
    logger.info("Participant notifications | sent=%s | failed=%s", sent, failed)


async def _notify_group_new_contest(bot: Bot, contest) -> None:
    if not GROUP_ID:
        return
    text = (
        f"🔥 <b>Новый конкурс #{contest.id}!</b>\n\n"
        f"📌 {contest.title}\n\n"
        f"💰 Приз: <b>{contest.prize_text}</b>\n"
        f"🏆 Победителей: <b>{contest.winners_count}</b>"
    )
    try:
        kb = group_contest_keyboard(BOT_USERNAME, contest.id) if BOT_USERNAME else None
        msg = await bot.send_message(GROUP_ID, text, parse_mode="HTML", reply_markup=kb)
        # Pin the announcement
        await bot.pin_chat_message(GROUP_ID, msg.message_id, disable_notification=True)
        logger.info("Group notified about new contest #%s", contest.id)
    except Exception as e:
        logger.warning("Group notification failed | %s", e)


async def _notify_group_draw(
    bot: Bot, contest_id: int, contest_title: str, winners_lines: list[str]
) -> None:
    if not GROUP_ID:
        return
    block = "\n".join(winners_lines)
    text = (
        f"🎊 <b>Конкурс #{contest_id} завершён!</b>\n\n"
        f"📌 {contest_title}\n\n"
        f"🏆 <b>Победители:</b>\n{block}"
    )
    try:
        await bot.send_message(GROUP_ID, text, parse_mode="HTML")
        logger.info("Group notified about draw #%s", contest_id)
    except Exception as e:
        logger.warning("Group draw notification failed | %s", e)


# ─── FSM cancel (universal) ───────────────────────────────────────────────────

@router.callback_query(F.data == "cancel_fsm")
async def cb_cancel_fsm(call: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    await _show_admin_panel(call, session, edit=True)


# ─── /ban /unban /list_users ──────────────────────────────────────────────────

@router.callback_query(F.data == "admin:users")
async def cb_admin_users(call: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True)
        return
    users = await repository.list_users(session)
    if not users:
        await call.message.edit_text("👥 Пользователей пока нет.", reply_markup=admin_panel_keyboard(False))
        await call.answer()
        return
    lines = [f"👥 <b>Пользователи ({len(users)}):</b>\n"]
    for u in users:
        name = f"@{u.username}" if u.username else "—"
        s = "🚫" if u.is_banned else "✅"
        lines.append(f"{s} <code>{u.telegram_id}</code> {name}")
    # Send as separate message to avoid edit limit
    await call.message.answer("\n".join(lines), parse_mode="HTML")
    await call.answer()


@router.message(Command("ban"))
async def cmd_ban(message: Message, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return
    args = message.text.split()
    if len(args) < 2 or not args[1].lstrip("-").isdigit():
        await message.answer("📖 /ban <telegram_id>")
        return
    user = await repository.set_ban(session, int(args[1]), True)
    name = f"@{user.username}" if user and user.username else f"<code>{args[1]}</code>"
    await message.answer(f"🚫 {name} заблокирован." if user else "❓ Не найден.", parse_mode="HTML")


@router.message(Command("unban"))
async def cmd_unban(message: Message, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return
    args = message.text.split()
    if len(args) < 2 or not args[1].lstrip("-").isdigit():
        await message.answer("📖 /unban <telegram_id>")
        return
    user = await repository.set_ban(session, int(args[1]), False)
    name = f"@{user.username}" if user and user.username else f"<code>{args[1]}</code>"
    await message.answer(f"✅ {name} разблокирован." if user else "❓ Не найден.", parse_mode="HTML")
