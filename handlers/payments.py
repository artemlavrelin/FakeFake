"""Balance, withdrawal, /addbalance, /minusbalance, /topbalance."""
from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from config import ADMIN_IDS, MODER_GROUP_ID
from database import repository
from states.contest import WithdrawFSM
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router()

WITHDRAW_COOLDOWN_HOURS = 36


def _admin_only(uid: int) -> bool:
    return uid in ADMIN_IDS


@router.callback_query(F.data == "my_stats_full")
async def cb_my_stats_full(call: CallbackQuery, session: AsyncSession) -> None:
    user    = await repository.get_or_create_user(session, call.from_user.id, call.from_user.username)
    balance = await repository.get_or_create_balance(session, call.from_user.id)
    stats   = await repository.get_user_stats(session, call.from_user.id)
    profile = user.profile
    from database.models import STATUS_ICONS
    num    = f"▫️{user.user_number}" if user.user_number else "▫️—"
    status = STATUS_ICONS.get(profile.status if profile else "new", "…..")
    total  = balance.balance + balance.paid_out

    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="menu"))
    b.row(InlineKeyboardButton(text="🌟 Вывод", callback_data="withdraw"))
    await call.message.edit_text(
        f"{status} {num}\n\n"
        f"<b>РОЗЫГРЫШ:</b>\n"
        f"🤽 {stats['participations']}   🏆 {stats['wins']}   💵 ${stats['prize_sum']:.2f}\n\n"
        f"⭐️ Баланс: <b>${balance.balance:.2f}</b>\n"
        f"💫 Выплачено: <b>${balance.paid_out:.2f}</b>\n"
        f"✨ Всего: <b>${total:.2f}</b>",
        parse_mode="HTML", reply_markup=b.as_markup(),
    )
    await call.answer()


@router.callback_query(F.data == "withdraw")
async def cb_withdraw(call: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    can, remaining = await repository.check_cooldown(
        session, call.from_user.id, "last_withdrawal_at", WITHDRAW_COOLDOWN_HOURS
    )
    if not can:
        secs = int(remaining.total_seconds())
        h, m = secs // 3600, (secs % 3600) // 60
        await call.answer(f"⏳ Следующий вывод через {h}ч {m}м.", show_alert=True); return

    balance = await repository.get_or_create_balance(session, call.from_user.id)
    if balance.balance <= 0:
        await call.answer("💰 Недостаточно средств.", show_alert=True); return

    await state.set_state(WithdrawFSM.waiting_amount)
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="⬅️ Отмена", callback_data="cancel_fsm"))
    await call.message.edit_text(
        f"🌟 <b>ВЫВОД СРЕДСТВ</b>\n\nДоступно: <b>${balance.balance:.2f}</b>\n\nВведите сумму:",
        parse_mode="HTML", reply_markup=b.as_markup(),
    )
    await call.answer()


@router.message(WithdrawFSM.waiting_amount)
async def fsm_withdraw_amount(message: Message, state: FSMContext, session: AsyncSession) -> None:
    raw = (message.text or "").strip().replace(",", ".")
    try:
        amount = float(raw)
        if amount <= 0: raise ValueError
    except ValueError:
        await message.answer("⚠️ Введите корректную сумму."); return

    balance = await repository.get_or_create_balance(session, message.from_user.id)
    if amount > balance.balance:
        await message.answer(f"⚠️ Недостаточно средств. Доступно: ${balance.balance:.2f}"); return

    await state.update_data(amount=amount)
    await state.set_state(WithdrawFSM.confirm)
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data="withdraw:confirm"),
        InlineKeyboardButton(text="❌ Отмена",      callback_data="cancel_fsm"),
    )
    await message.answer(f"Подтвердите вывод <b>${amount:.2f}</b>?",
                         parse_mode="HTML", reply_markup=b.as_markup())


@router.callback_query(WithdrawFSM.confirm, F.data == "withdraw:confirm")
async def cb_withdraw_confirm(call: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    data   = await state.get_data()
    amount = data.get("amount", 0)
    await state.clear()

    user    = await repository.get_or_create_user(session, call.from_user.id, call.from_user.username)
    balance = await repository.get_or_create_balance(session, call.from_user.id)
    if amount > balance.balance:
        await call.answer("⚠️ Недостаточно средств.", show_alert=True); return

    wr    = await repository.create_withdrawal(session, call.from_user.id, amount)
    await repository.set_timestamp(session, call.from_user.id, "last_withdrawal_at")

    uname = f"@{user.username}" if user.username else f"id{user.telegram_id}"
    num   = f"▫️{user.user_number}" if user.user_number else ""
    pd    = user.payment
    moder_text = (
        f"#вывод\n"
        f"ID: <code>{user.telegram_id}</code> {uname} {num}\n"
        f"Сумма: <b>${amount:.2f}</b>\n\n"
        f"💛 Binance: <code>{pd.binance_id if pd and pd.binance_id else '—'}</code>\n"
        f"🎰 Stake: <code>{pd.stake_user if pd and pd.stake_user else '—'}</code>"
    )
    moder_kb = InlineKeyboardBuilder()
    moder_kb.row(
        InlineKeyboardButton(text="✅ OK",    callback_data=f"wd:ok:{wr.id}"),
        InlineKeyboardButton(text="❌ Отказ", callback_data=f"wd:no:{wr.id}"),
    )
    if MODER_GROUP_ID:
        try:
            sent = await bot.send_message(MODER_GROUP_ID, moder_text,
                                           parse_mode="HTML", reply_markup=moder_kb.as_markup())
            await repository.update_withdrawal(session, wr.id, "pending", sent.message_id)
        except Exception as e:
            logger.warning("Withdrawal notify failed | %s", e)

    await call.message.edit_text(f"✅ Заявка на вывод <b>${amount:.2f}</b> отправлена.", parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("wd:ok:"))
async def cb_wd_ok(call: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    if not _admin_only(call.from_user.id):
        await call.answer("⛔", show_alert=True); return
    wr_id = int(call.data.split(":")[2])
    wr    = await repository.get_withdrawal(session, wr_id)
    if not wr or wr.status != "pending":
        await call.answer("Уже обработано.", show_alert=True); return
    await repository.withdraw_balance(session, wr.telegram_id, wr.amount)
    await repository.update_withdrawal(session, wr_id, "approved")
    try:
        await call.message.edit_text(
            call.message.text + f"\n\n✅ Одобрено @{call.from_user.username}", parse_mode="HTML")
    except Exception: pass
    try:
        await bot.send_message(wr.telegram_id,
            f"✅ Вывод <b>${wr.amount:.2f}</b> одобрен!", parse_mode="HTML")
    except Exception: pass
    await call.answer("✅ Одобрено")


@router.callback_query(F.data.startswith("wd:no:"))
async def cb_wd_no(call: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    if not _admin_only(call.from_user.id):
        await call.answer("⛔", show_alert=True); return
    wr_id = int(call.data.split(":")[2])
    wr    = await repository.get_withdrawal(session, wr_id)
    if not wr or wr.status != "pending":
        await call.answer("Уже обработано.", show_alert=True); return
    await repository.update_withdrawal(session, wr_id, "rejected")
    try:
        await call.message.edit_text(
            call.message.text + f"\n\n❌ Отклонено @{call.from_user.username}", parse_mode="HTML")
    except Exception: pass
    try:
        await bot.send_message(wr.telegram_id,
            f"❌ Вывод <b>${wr.amount:.2f}</b> отклонён.", parse_mode="HTML")
    except Exception: pass
    await call.answer("❌ Отклонено")


# ─── Admin: /addbalance and /minusbalance ─────────────────────────────────────

@router.message(Command("addbalance"))
async def cmd_addbalance(message: Message, session: AsyncSession) -> None:
    if not _admin_only(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("📖 /addbalance @username|id сумма"); return
    target, amount_str = parts[1], parts[2]
    try:
        amount = float(amount_str.replace(",", "."))
        if amount <= 0: raise ValueError
    except ValueError:
        await message.answer("⚠️ Неверная сумма"); return

    user = (await repository.get_user_by_username(session, target)
             if target.startswith("@")
             else await repository.get_user(session, int(target)) if target.lstrip("-").isdigit()
             else None)
    if not user:
        await message.answer("❓ Не найден"); return

    b = await repository.add_balance(session, user.telegram_id, amount)
    await message.answer(
        f"✅ Начислено <b>${amount:.2f}</b> → <code>{user.telegram_id}</code>\n"
        f"Баланс: <b>${b.balance:.2f}</b>",
        parse_mode="HTML",
    )


@router.message(Command("minusbalance"))
async def cmd_minusbalance(message: Message, session: AsyncSession) -> None:
    """Subtract from balance only — does NOT add to paid_out."""
    if not _admin_only(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("📖 /minusbalance @username|id сумма"); return
    target, amount_str = parts[1], parts[2]
    try:
        amount = float(amount_str.replace(",", "."))
        if amount <= 0: raise ValueError
    except ValueError:
        await message.answer("⚠️ Неверная сумма"); return

    user = (await repository.get_user_by_username(session, target)
             if target.startswith("@")
             else await repository.get_user(session, int(target)) if target.lstrip("-").isdigit()
             else None)
    if not user:
        await message.answer("❓ Не найден"); return

    b = await repository.subtract_balance_only(session, user.telegram_id, amount)
    await message.answer(
        f"✅ Списано <b>${amount:.2f}</b> с <code>{user.telegram_id}</code>\n"
        f"Остаток: <b>${b.balance:.2f}</b>",
        parse_mode="HTML",
    )


@router.message(Command("topbalance"))
async def cmd_topbalance(message: Message, session: AsyncSession) -> None:
    rows = await repository.top_balances(session, limit=10)
    if not rows:
        await message.answer("👥 Нет данных"); return
    medals = ["🥇", "🥈", "🥉"]
    lines  = ["💰 <b>ТОП БАЛАНС</b>\n"]
    for i, (bal, user) in enumerate(rows):
        medal = medals[i] if i < 3 else f"{i+1}."
        name  = f"@{user.username}" if user.username else f"▫️{user.user_number}"
        lines.append(f"{medal} {name} — <b>${bal.balance:.2f}</b>")
    await message.answer("\n".join(lines), parse_mode="HTML")
