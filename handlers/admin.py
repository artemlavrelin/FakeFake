import asyncio
import math

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramRetryAfter
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import ADMIN_IDS, BOT_LINK, GROUP_ID
from database import repository
from keyboards.inline import (
    admin_panel_keyboard,
    broadcast_confirm_keyboard,
    cancel_contest_confirm_keyboard,
    cancel_keyboard,
    edit_contest_keyboard,
    group_contest_keyboard,
    group_draw_keyboard,
    payments_page_keyboard,
)
from states.contest import Broadcast, CreateContest, EditContest
from utils.formatters import format_winner, stats_bar
from utils.logger import get_logger
from utils.time_utils import time_ago

logger = get_logger(__name__)
router = Router()

EDIT_FIELD_LABELS = {
    "title":         "описание конкурса",
    "prize_text":    "текст приза",
    "prize_amount":  "сумму приза (число)",
    "winners_count": "количество победителей (число)",
}


def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS


# ─── Retry helper ─────────────────────────────────────────────────────────────

async def _send_with_retry(bot: Bot, chat_id: int, text: str, reply_markup=None, max_tries: int = 3) -> None:
    for attempt in range(max_tries):
        try:
            await bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=reply_markup)
            return
        except TelegramRetryAfter as e:
            wait = min(e.retry_after, 60)
            logger.warning("Flood control | chat=%s | wait=%ss", chat_id, e.retry_after)
            await asyncio.sleep(wait)
        except Exception as e:
            logger.warning("Send failed | chat=%s | %s", chat_id, e)
            return
    logger.error("Gave up sending to chat=%s after %s attempts", chat_id, max_tries)


# ─── /admin ───────────────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return
    await _show_panel(message, session, edit=False)


@router.callback_query(F.data == "admin:panel")
async def cb_admin_panel(call: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True)
        return
    await _show_panel(call, session, edit=True)


async def _show_panel(event, session: AsyncSession, edit: bool) -> None:
    contest    = await repository.get_active_contest(session)
    has_active = contest is not None

    if has_active:
        count = await repository.get_participant_count(session, contest.id)
        bar   = stats_bar(time_ago(contest.created_at), count, contest.winners_count, contest.prize_text, 0)
        text  = (
            f"🔧 <b>ПАНЕЛЬ АДМИНИСТРАТОРА</b>\n\n"
            f"🤹🏻 Активный конкурс: <b>#{contest.id}</b>\n"
            f"📌 {contest.title}\n{bar}"
        )
    else:
        text = "🔧 <b>ПАНЕЛЬ АДМИНИСТРАТОРА</b>\n\nАктивных конкурсов нет."

    kb  = admin_panel_keyboard(has_active)
    msg = event.message if isinstance(event, CallbackQuery) else event
    if edit:
        await msg.edit_text(text, parse_mode="HTML", reply_markup=kb)
        await event.answer()
    else:
        await msg.answer(text, parse_mode="HTML", reply_markup=kb)


# ─── Create contest ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:create")
async def cb_create(call: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True)
        return
    if await repository.get_active_contest(session):
        await call.answer("⚠️ Уже есть активный конкурс.", show_alert=True)
        return
    await state.set_state(CreateContest.waiting_title)
    await call.message.edit_text(
        "📝 <b>Создание конкурса — шаг 1/4</b>\n\n📌 Введите <b>описание конкурса</b>:",
        parse_mode="HTML", reply_markup=cancel_keyboard("ru"),
    )
    await call.answer()


@router.message(CreateContest.waiting_title)
async def fsm_title(message: Message, state: FSMContext) -> None:
    if not message.text or len(message.text.strip()) < 3:
        await message.answer("⚠️ Минимум 3 символа:")
        return
    await state.update_data(title=message.text.strip())
    await state.set_state(CreateContest.waiting_prize_text)
    await message.answer("Шаг 2/4 — <b>Текст приза</b>:", parse_mode="HTML", reply_markup=cancel_keyboard("ru"))


@router.message(CreateContest.waiting_prize_text)
async def fsm_prize_text(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("⚠️ Введите текст:")
        return
    await state.update_data(prize_text=message.text.strip())
    await state.set_state(CreateContest.waiting_prize_amount)
    await message.answer(
        "Шаг 3/4 — <b>Сумма приза числом</b> (или <code>0</code>):",
        parse_mode="HTML", reply_markup=cancel_keyboard("ru"),
    )


@router.message(CreateContest.waiting_prize_amount)
async def fsm_prize_amount(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip().replace(",", ".")
    try:
        amount = float(raw)
        if amount < 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Введите число:")
        return
    await state.update_data(prize_amount=amount)
    await state.set_state(CreateContest.waiting_winners_count)
    await message.answer("Шаг 4/4 — <b>Количество победителей</b> (1–100):", parse_mode="HTML", reply_markup=cancel_keyboard("ru"))


@router.message(CreateContest.waiting_winners_count)
async def fsm_winners_count(message: Message, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    raw = (message.text or "").strip()
    if not raw.isdigit() or not (1 <= int(raw) <= 100):
        await message.answer("⚠️ Число от 1 до 100:")
        return
    data = await state.get_data()
    await state.clear()
    contest = await repository.create_contest(
        session, title=data["title"], prize_text=data["prize_text"],
        prize_amount=data["prize_amount"], winners_count=int(raw),
    )
    await message.answer(
        f"✅ <b>Конкурс #{contest.id} создан!</b>\n\n"
        f"📌 {contest.title}\n💰 {contest.prize_text}\n🏆 Победителей: <b>{contest.winners_count}</b>",
        parse_mode="HTML", reply_markup=admin_panel_keyboard(True),
    )
    await _group_new_contest(bot, contest)


# ─── Edit ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:edit")
async def cb_edit(call: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True)
        return
    contest = await repository.get_active_contest(session)
    if not contest:
        await call.answer("Нет активного конкурса.", show_alert=True)
        return
    await state.set_state(EditContest.choosing_field)
    await call.message.edit_text(
        f"✏️ <b>Редактирование #{contest.id}</b>\n\nЧто изменить?",
        parse_mode="HTML", reply_markup=edit_contest_keyboard(),
    )
    await call.answer()


@router.callback_query(F.data.startswith("edit:"))
async def cb_edit_field(call: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True)
        return
    field = call.data.split(":")[1]
    await state.update_data(edit_field=field)
    await state.set_state(EditContest.waiting_value)
    await call.message.edit_text(
        f"✏️ Новое <b>{EDIT_FIELD_LABELS.get(field, field)}</b>:",
        parse_mode="HTML", reply_markup=cancel_keyboard("ru"),
    )
    await call.answer()


@router.message(EditContest.waiting_value)
async def fsm_edit_value(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data  = await state.get_data()
    field = data.get("edit_field", "")
    raw   = (message.text or "").strip()
    if field == "prize_amount":
        try:
            value = float(raw.replace(",", "."))
        except ValueError:
            await message.answer("⚠️ Введите число:")
            return
    elif field == "winners_count":
        if not raw.isdigit() or not (1 <= int(raw) <= 100):
            await message.answer("⚠️ Число от 1 до 100:")
            return
        value = int(raw)
    else:
        value = raw
    await state.clear()
    contest = await repository.get_active_contest(session)
    if not contest:
        await message.answer("⚠️ Нет активного конкурса.")
        return
    await repository.edit_contest(session, contest, field, value)
    await message.answer(
        f"✅ «{EDIT_FIELD_LABELS.get(field, field)}» обновлено.",
        parse_mode="HTML", reply_markup=admin_panel_keyboard(True),
    )


# ─── Cancel contest ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:cancel_contest")
async def cb_cancel_contest(call: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True)
        return
    contest = await repository.get_active_contest(session)
    if not contest:
        await call.answer("Нет конкурса.", show_alert=True)
        return
    await call.message.edit_text(
        f"🚫 <b>Отменить #{contest.id}?</b>\n\n📌 {contest.title}",
        parse_mode="HTML", reply_markup=cancel_contest_confirm_keyboard(),
    )
    await call.answer()


@router.callback_query(F.data == "admin:cancel_contest_yes")
async def cb_cancel_yes(call: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True)
        return
    contest = await repository.get_active_contest(session)
    if not contest:
        await call.answer("Нет конкурса.", show_alert=True)
        return
    await repository.cancel_contest(session, contest)
    await call.message.edit_text(
        f"🚫 Конкурс <b>#{contest.id}</b> отменён.",
        parse_mode="HTML", reply_markup=admin_panel_keyboard(False),
    )
    await call.answer()


# ─── Draw ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:draw")
async def cb_draw(call: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
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


async def _run_draw(msg: Message, session: AsyncSession, bot: Bot, edit: bool) -> None:
    contest = await repository.get_active_contest(session)
    if not contest:
        text = "😔 Нет активного конкурса."
        await (msg.edit_text(text) if edit else msg.answer(text))
        return

    count = await repository.get_participant_count(session, contest.id)
    if count == 0:
        text = f"⚠️ Нет участников в <b>#{contest.id}</b>."
        await (msg.edit_text(text, parse_mode="HTML") if edit else msg.answer(text, parse_mode="HTML"))
        return

    winners, total = await repository.draw_winners(session, contest)
    winner_ids    = {w.telegram_id for w in winners}
    winners_lines = [
        format_winner(w.telegram_id, w.user.username if w.user else None, i + 1)
        for i, w in enumerate(winners)
    ]
    finished = contest.finished_at.strftime("%d.%m.%Y %H:%M") if contest.finished_at else "—"

    result_text = (
        f"🎊 <b>Розыгрыш завершён!</b>\n\n"
        f"🤹🏻 Конкурс: <b>#{contest.id}</b>\n"
        f"📌 {contest.title}\n💰 {contest.prize_text}\n"
        f"👥 Участников: <b>{total}</b>  📅 {finished}\n\n"
        f"🏆 <b>Победители ({len(winners)}):</b>\n" + "\n".join(winners_lines)
    )

    if edit:
        await msg.edit_text(result_text, parse_mode="HTML", reply_markup=admin_panel_keyboard(False))
    else:
        await msg.answer(result_text, parse_mode="HTML")

    all_parts = await repository.get_all_participants(session, contest.id)
    await _notify_participants(
        bot, session, [p.telegram_id for p in all_parts],
        winner_ids, contest.title, contest.prize_text, winners_lines,
    )
    await _group_draw(bot, contest.id, contest.title, winners_lines)


# ─── Broadcast ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:broadcast")
async def cb_broadcast(call: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True)
        return
    await state.set_state(Broadcast.waiting_message)
    await call.message.edit_text(
        "📣 <b>Рассылка</b>\n\nВведите текст:",
        parse_mode="HTML", reply_markup=cancel_keyboard("ru"),
    )
    await call.answer()


@router.message(Broadcast.waiting_message)
async def fsm_broadcast(message: Message, state: FSMContext, session: AsyncSession) -> None:
    user_ids = await repository.get_all_user_ids(session)
    await state.update_data(text=message.text)
    await state.set_state(Broadcast.confirm)
    await message.answer(
        f"📣 <b>Предпросмотр</b>\n\n──────\n{message.text}\n──────\n\n"
        f"👥 Получателей: <b>{len(user_ids)}</b>\n\nОтправить?",
        parse_mode="HTML", reply_markup=broadcast_confirm_keyboard(),
    )


@router.callback_query(F.data == "broadcast:send")
async def cb_broadcast_send(call: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True)
        return
    data     = await state.get_data()
    text     = data.get("text", "")
    await state.clear()
    user_ids = await repository.get_all_user_ids(session)
    await call.message.edit_text(f"📣 Рассылка... ({len(user_ids)} чел.)")
    await call.answer()
    sent = failed = 0
    for uid in user_ids:
        try:
            await bot.send_message(uid, text)
            sent += 1
        except Exception as e:
            logger.warning("Broadcast fail | %s | %s", uid, e)
            failed += 1
        await asyncio.sleep(0.05)
    logger.info("Broadcast | sent=%s | failed=%s", sent, failed)
    await call.message.answer(
        f"✅ Рассылка завершена\n📤 {sent}  ❌ {failed}",
        parse_mode="HTML", reply_markup=admin_panel_keyboard(False),
    )


# ─── Users ────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:users")
async def cb_users(call: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True)
        return
    users = await repository.list_users(session)
    if not users:
        await call.message.answer("👥 Нет пользователей.")
        await call.answer()
        return
    lines = [f"👥 <b>Пользователи ({len(users)}):</b>\n"]
    for u in users:
        name = f"@{u.username}" if u.username else "—"
        num  = f"▫️{u.user_number}" if u.user_number else ""
        flag = "🇷🇺" if u.lang == "ru" else "🇬🇧" if u.lang == "en" else "❓"
        s    = "🚫" if u.is_banned else "✅"
        lines.append(f"{s} <code>{u.telegram_id}</code> {name} {num} {flag}")
    for i in range(0, len(lines), 50):
        await call.message.answer("\n".join(lines[i:i + 50]), parse_mode="HTML")
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


# ─── Payments ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:payments")
async def cb_payments(call: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True)
        return
    await _show_payments(call.message, session, page=0, edit=True)
    await call.answer()


@router.callback_query(F.data.startswith("payments:page:"))
async def cb_payments_page(call: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True)
        return
    page = int(call.data.split(":")[2])
    await _show_payments(call.message, session, page=page, edit=True)
    await call.answer()


async def _show_payments(msg: Message, session: AsyncSession, page: int, edit: bool) -> None:
    page_size = 15
    records, total = await repository.list_payment_data(session, page=page, page_size=page_size)
    total_pages    = max(1, math.ceil(total / page_size))
    if not records:
        text = "💳 <b>Платёжные данные</b>\n\nПока нет записей."
    else:
        lines = [f"💳 <b>Платёжные данные</b> (стр. {page + 1}/{total_pages})\n"]
        for r in records:
            name    = f"@{r.user.username}" if r.user and r.user.username else "—"
            num     = f"▫️{r.user.user_number}" if r.user and r.user.user_number else ""
            binance = r.binance_id or "—"
            stake   = r.stake_user or "—"
            lines.append(f"• <code>{r.telegram_id}</code> {name} {num}\n  💛 {binance}  🎰 {stake}")
        text = "\n".join(lines)
    kb = payments_page_keyboard(page, total_pages)
    if edit:
        await msg.edit_text(text, parse_mode="HTML", reply_markup=kb)
    else:
        await msg.answer(text, parse_mode="HTML", reply_markup=kb)


@router.message(Command("payment_view"))
async def cmd_payment_view(message: Message, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return
    args = message.text.split()
    if len(args) < 2 or not args[1].lstrip("-").isdigit():
        await message.answer("📖 /payment_view <telegram_id>")
        return
    tid  = int(args[1])
    user = await repository.get_user(session, tid)
    pd   = await repository.get_payment_data(session, tid)
    if not user:
        await message.answer(f"❓ <code>{tid}</code> не найден.", parse_mode="HTML")
        return
    name    = f"@{user.username}" if user.username else "—"
    num     = f"▫️{user.user_number}" if user.user_number else "—"
    binance = pd.binance_id if pd and pd.binance_id else "—"
    stake   = pd.stake_user if pd and pd.stake_user else "—"
    await message.answer(
        f"💳 <b>Платёжные данные</b>\n\n👤 {name}  {num}\n🆔 <code>{tid}</code>\n\n"
        f"💛 Binance ID: <code>{binance}</code>\n🎰 Stake username: <code>{stake}</code>",
        parse_mode="HTML",
    )


@router.message(Command("payment_set"))
async def cmd_payment_set(message: Message, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("📖 /payment_set <telegram_id> binance=ID stake=username")
        return
    if not parts[1].lstrip("-").isdigit():
        await message.answer("⚠️ Неверный telegram_id.")
        return
    tid        = int(parts[1])
    binance_id = next((p.split("=", 1)[1] for p in parts[2:] if p.lower().startswith("binance=")), None)
    stake_user = next((p.split("=", 1)[1] for p in parts[2:] if p.lower().startswith("stake=")),   None)
    pd = await repository.upsert_payment_data(session, tid, binance_id=binance_id, stake_user=stake_user)
    await message.answer(
        f"✅ <code>{tid}</code>\n💛 Binance: <code>{pd.binance_id or '—'}</code>\n"
        f"🎰 Stake: <code>{pd.stake_user or '—'}</code>",
        parse_mode="HTML",
    )


# ─── FSM cancel (admin) ───────────────────────────────────────────────────────

@router.callback_query(F.data == "cancel_fsm")
async def cb_cancel_fsm(call: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    await _show_panel(call, session, edit=True)


# ─── Group notifications ──────────────────────────────────────────────────────

async def _group_new_contest(bot: Bot, contest) -> None:
    if not GROUP_ID:
        return
    text = (
        f"🤹🏻 <b>Новый конкурс #{contest.id}!</b>\n\n"
        f"📌 {contest.title}\n\n"
        f"💰 Приз: <b>{contest.prize_text}</b>\n"
        f"🏆 Победителей: <b>{contest.winners_count}</b>\n👥 Участников: <b>0</b>"
    )
    try:
        kb  = group_contest_keyboard(BOT_LINK, contest.id)
        msg = await bot.send_message(GROUP_ID, text, parse_mode="HTML", reply_markup=kb)
        logger.info("Group notified | contest #%s", contest.id)
    except Exception as e:
        logger.warning("Group notify send failed | %s", e)
        return
    try:
        await bot.pin_chat_message(GROUP_ID, msg.message_id, disable_notification=True)
    except Exception as e:
        logger.info("Pin skipped | %s", e)


async def _group_draw(bot: Bot, contest_id: int, title: str, winners_lines: list[str]) -> None:
    if not GROUP_ID:
        return
    block = "\n".join(winners_lines)
    text  = f"🎊 <b>Конкурс #{contest_id} завершён!</b>\n\n📌 {title}\n\n🏆 <b>Победители:</b>\n{block}"
    await _send_with_retry(bot, GROUP_ID, text, group_draw_keyboard(BOT_LINK))


async def _notify_participants(
    bot: Bot, session: AsyncSession,
    participant_ids: list[int], winner_ids: set[int],
    contest_title: str, prize_text: str, winners_lines: list[str],
) -> None:
    block = "\n".join(winners_lines)
    sent = failed = 0
    for uid in participant_ids:
        try:
            user = await repository.get_user(session, uid)
            lang = (user.lang or "ru") if user else "ru"
            if uid in winner_ids:
                text = t(lang, "notify_winner", title=contest_title, prize=prize_text)
            else:
                text = t(lang, "notify_other", title=contest_title, winners=block)
            await bot.send_message(uid, text, parse_mode="HTML")
            sent += 1
        except Exception as e:
            logger.warning("Notify fail | %s | %s", uid, e)
            failed += 1
        await asyncio.sleep(0.05)
    logger.info("Notifications | sent=%s | failed=%s", sent, failed)


@router.message(Command("loot"))
async def cmd_loot_ban(message: Message, session: AsyncSession) -> None:
    """Permanently disable loot for a user."""
    if not is_admin(message.from_user.id):
        return
    args = message.text.split()
    if len(args) < 2 or not args[1].lstrip("-").isdigit():
        await message.answer("📖 /loot <telegram_id>")
        return
    user = await repository.set_loot_ban(session, int(args[1]), True)
    name = f"@{user.username}" if user and user.username else f"<code>{args[1]}</code>"
    await message.answer(
        f"🔒 Loot заблокирован для {name}." if user else "❓ Не найден.",
        parse_mode="HTML",
    )
