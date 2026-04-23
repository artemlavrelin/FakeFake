"""
🫶 ПОЛУЧИТЬ ПРИЗ — loot system.
Entry screen shows Binance/Stake registration links.
If data present — screenshot flow + random prize.
"""
import random

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import BINANCE_URL, LOOT_COOLDOWN_HOURS, MODER_GROUP_ID, STAKE_URL
from database import repository
from keyboards.inline import (
    back_to_menu_keyboard, cancel_keyboard,
    loot_entry_keyboard, loot_roll_keyboard, loot_start_keyboard,
)
from states.contest import LootFSM
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router()

_PRIZES = [
    (90.000, 0.10),
    (10.000, 0.20),
    ( 5.000, 0.30),
    ( 3.000, 0.40),
    ( 2.000, 0.50),
    ( 1.000, 1.00),
    ( 0.500, 2.00),
    ( 0.100, 5.00),
    ( 0.001, 10.00),
]
_WEIGHTS = [p[0] for p in _PRIZES]
_AMOUNTS = [p[1] for p in _PRIZES]

LOOT_ENTRY_TEXT = (
    "🫶 <b>ПОЛУЧИТЬ ПРИЗ</b>\n\n"
    "Чтобы быстрее, чаще и проще отправлять деньги большему количеству людей, "
    "мы перешли на выплаты в крипте и используем две платформы: Binance и Stake.\n\n"
    "Если ты хочешь полноценно сотрудничать с нами, участвовать во всех розыгрышах "
    "и крипто-гемблинг активностях, а также получать выплаты — укажи свой ID или "
    "пройди регистрацию, если у тебя ещё нет аккаунта.\n\n"
    "При регистрации по нашим реферальным ссылкам ты получаешь от биржи скидки "
    "на комиссию и приветственные бонусы, а также дополнительный денежный бонус "
    "от нас — после верификации."
)


async def _lang(session: AsyncSession, tid: int) -> str:
    user = await repository.get_user(session, tid)
    return (user.lang or "ru") if user else "ru"


@router.callback_query(F.data == "loot")
async def cb_loot(call: CallbackQuery, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    user = await repository.get_or_create_user(session, call.from_user.id, call.from_user.username)

    if user.loot_banned:
        await call.answer("👉 Вы уже получили свой приз", show_alert=True); return

    can, remaining = await repository.check_cooldown(
        session, call.from_user.id, "last_loot_at", LOOT_COOLDOWN_HOURS
    )
    if not can:
        secs = int(remaining.total_seconds())
        h, m = secs // 3600, (secs % 3600) // 60
        await call.answer(f"⏳ Следующий приз через {h}ч {m}м.", show_alert=True); return

    pd       = await repository.get_payment_data(session, call.from_user.id)
    has_data = pd and pd.binance_id and pd.stake_user

    if not has_data:
        await call.message.edit_text(
            LOOT_ENTRY_TEXT,
            parse_mode="HTML",
            reply_markup=loot_entry_keyboard(lang, STAKE_URL, BINANCE_URL),
        )
        await call.answer(); return

    await call.message.edit_text(
        f"🫶 <b>ПОЛУЧИТЬ ПРИЗ</b>\n\n"
        f"🟨 Binance ID: <code>{pd.binance_id}</code>\n"
        f"♠️ Stake: <code>{pd.stake_user}</code>\n\n"
        f"Нажмите кнопку, чтобы начать:",
        parse_mode="HTML",
        reply_markup=loot_start_keyboard(lang),
    )
    await call.answer()


@router.callback_query(F.data == "loot:start")
async def cb_loot_start(call: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    user = await repository.get_or_create_user(session, call.from_user.id, call.from_user.username)
    if user.loot_banned:
        await call.answer("👉 Вы уже получили свой приз", show_alert=True); return
    can, remaining = await repository.check_cooldown(
        session, call.from_user.id, "last_loot_at", LOOT_COOLDOWN_HOURS
    )
    if not can:
        secs = int(remaining.total_seconds())
        h, m = secs // 3600, (secs % 3600) // 60
        await call.answer(f"⏳ {h}ч {m}м.", show_alert=True); return

    await state.set_state(LootFSM.waiting_binance_screenshot)
    await call.message.edit_text(
        "📸 Отправьте <b>скриншот вашего Binance ID</b>:",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(lang, back_cb="loot"),
    )
    await call.answer()


@router.message(LootFSM.waiting_binance_screenshot, F.photo | F.text)
async def fsm_binance_screenshot(message: Message, state: FSMContext, session: AsyncSession) -> None:
    lang = await _lang(session, message.from_user.id)
    file_id = message.photo[-1].file_id if message.photo else f"text:{message.text or ''}"
    await state.update_data(binance_file_id=file_id)
    await state.set_state(LootFSM.waiting_stake_screenshot)
    await message.answer(
        "📸 Отправьте <b>скриншот вашего Stake username</b>:",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(lang, back_cb="loot"),
    )


@router.message(LootFSM.waiting_stake_screenshot, F.photo | F.text)
async def fsm_stake_screenshot(message: Message, state: FSMContext, session: AsyncSession) -> None:
    lang = await _lang(session, message.from_user.id)
    file_id = message.photo[-1].file_id if message.photo else f"text:{message.text or ''}"
    await state.update_data(stake_file_id=file_id)
    await state.set_state(LootFSM.confirm)
    await message.answer(
        "✅ Скриншоты получены. Нажмите кнопку для розыгрыша:",
        reply_markup=loot_roll_keyboard(lang),
    )


@router.callback_query(LootFSM.confirm, F.data == "loot:roll")
async def cb_loot_roll(call: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    lang = await _lang(session, call.from_user.id)
    user = await repository.get_or_create_user(session, call.from_user.id, call.from_user.username)

    if user.loot_banned:
        await state.clear()
        await call.answer("👉 Вы уже получили свой приз", show_alert=True); return

    can, remaining = await repository.check_cooldown(
        session, call.from_user.id, "last_loot_at", LOOT_COOLDOWN_HOURS
    )
    if not can:
        await state.clear()
        secs = int(remaining.total_seconds())
        h, m = secs // 3600, (secs % 3600) // 60
        await call.answer(f"⏳ {h}ч {m}м.", show_alert=True); return

    data = await state.get_data()
    await state.clear()

    prize = random.choices(_AMOUNTS, weights=_WEIGHTS, k=1)[0]
    await repository.set_timestamp(session, call.from_user.id, "last_loot_at")
    logger.info("Loot roll | telegram_id=%s | prize=$%s", call.from_user.id, prize)

    await call.message.edit_text(
        f"🎉 <b>Поздравляем!</b>\n\n"
        f"Вы выиграли: <b>${prize}</b>\n\n"
        f"После проверки сумма будет отправлена на ваш баланс Stake или Binance.",
        parse_mode="HTML",
        reply_markup=back_to_menu_keyboard(lang),
    )
    await call.answer()

    if MODER_GROUP_ID:
        pd    = await repository.get_payment_data(session, call.from_user.id)
        uname = call.from_user.username or "(нет username)"
        num   = user.user_number or "—"
        binance_fid = data.get("binance_file_id", "")
        stake_fid   = data.get("stake_file_id", "")
        header = (
            f"LOOT ЗАЯВКА\n\n"
            f"@{uname} | {call.from_user.id} | {num}\n"
            f"Выигрыш: ${prize}\n"
            f"Binance: {pd.binance_id if pd and pd.binance_id else '—'}\n"
            f"Stake: {pd.stake_user if pd and pd.stake_user else '—'}"
        )
        try:
            await bot.send_message(MODER_GROUP_ID, header)
            for label, fid in [("Binance", binance_fid), ("Stake", stake_fid)]:
                if not fid:
                    continue
                if fid.startswith("text:"):
                    await bot.send_message(MODER_GROUP_ID, f"{label}: {fid[5:]}")
                else:
                    await bot.send_photo(MODER_GROUP_ID, fid, caption=f"Скриншот {label}")
        except Exception as e:
            logger.warning("Loot moder notify | %s", e)


@router.message(Command("loot"))
async def cmd_loot_ban(message: Message, session: AsyncSession) -> None:
    from config import ADMIN_IDS
    if message.from_user.id not in ADMIN_IDS:
        return
    args = message.text.split()
    if len(args) < 2 or not args[1].lstrip("-").isdigit():
        await message.answer("Использование: /loot [telegram_id]"); return
    user = await repository.set_loot_ban(session, int(args[1]), True)
    name = f"@{user.username}" if user and user.username else args[1]
    await message.answer(f"Loot заблокирован для {name}" if user else "Не найден")
