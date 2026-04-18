"""
📫 Получить приз — loot system with screenshot verification and random prizes.
"""
import random

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import BINANCE_URL, LOOT_COOLDOWN_HOURS, MODER_GROUP_ID, STAKE_URL
from database import repository
from strings import t
from keyboards.inline import (
    back_to_menu_keyboard, cancel_keyboard,
    loot_no_data_keyboard, loot_roll_keyboard, loot_start_keyboard,
    main_menu_keyboard,
)
from states.contest import LootFSM
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router()

# Prize table: (weight, dollar_amount)
_PRIZES = [
    (90.0,  0.10),
    (10.0,  0.20),
    (5.0,   0.30),
    (3.0,   0.40),
    (2.0,   0.50),
    (1.0,   1.00),
    (0.5,   2.00),
    (0.1,   5.00),
    (0.001, 10.00),
]
_WEIGHTS = [p[0] for p in _PRIZES]
_AMOUNTS = [p[1] for p in _PRIZES]


def _roll_prize() -> float:
    return random.choices(_AMOUNTS, weights=_WEIGHTS, k=1)[0]


async def _lang(session: AsyncSession, tid: int) -> str:
    user = await repository.get_user(session, tid)
    return (user.lang or "ru") if user else "ru"


# ─── Entry point (main menu → 📫 Получить приз) ───────────────────────────────

@router.callback_query(F.data == "loot")
async def cb_loot(call: CallbackQuery, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    user = await repository.get_or_create_user(session, call.from_user.id, call.from_user.username)

    if user.loot_banned:
        await call.answer(t(lang, "loot_banned_msg"), show_alert=True)
        return

    # 24h cooldown check
    can, remaining = await repository.check_cooldown(
        session, call.from_user.id, "last_loot_at", LOOT_COOLDOWN_HOURS
    )
    if not can:
        secs = int(remaining.total_seconds())
        h, m = secs // 3600, (secs % 3600) // 60
        await call.answer(t(lang, "loot_cooldown", h=h, m=m), show_alert=True)
        return

    pd       = await repository.get_payment_data(session, call.from_user.id)
    has_data = pd and pd.binance_id and pd.stake_user

    if not has_data:
        await call.message.edit_text(
            t(lang, "loot_no_data"),
            parse_mode="HTML",
            reply_markup=loot_no_data_keyboard(lang, STAKE_URL, BINANCE_URL),
        )
        await call.answer()
        return

    await call.message.edit_text(
        t(lang, "loot_start_text", binance=pd.binance_id, stake=pd.stake_user),
        parse_mode="HTML",
        reply_markup=loot_start_keyboard(lang),
    )
    await call.answer()


# ─── Step 1: Start — request Binance screenshot ───────────────────────────────

@router.callback_query(F.data == "loot:start")
async def cb_loot_start(call: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    user = await repository.get_or_create_user(session, call.from_user.id, call.from_user.username)

    if user.loot_banned:
        await call.answer(t(lang, "loot_banned_msg"), show_alert=True)
        return

    can, remaining = await repository.check_cooldown(
        session, call.from_user.id, "last_loot_at", LOOT_COOLDOWN_HOURS
    )
    if not can:
        secs = int(remaining.total_seconds())
        h, m = secs // 3600, (secs % 3600) // 60
        await call.answer(t(lang, "loot_cooldown", h=h, m=m), show_alert=True)
        return

    await state.set_state(LootFSM.waiting_binance_screenshot)
    await call.message.edit_text(
        t(lang, "loot_send_binance"),
        parse_mode="HTML",
        reply_markup=cancel_keyboard(lang, back_cb="loot"),
    )
    await call.answer()


# ─── Step 2: Receive Binance screenshot ───────────────────────────────────────

@router.message(LootFSM.waiting_binance_screenshot, F.photo | F.text)
async def fsm_loot_binance(message: Message, state: FSMContext, session: AsyncSession) -> None:
    lang = await _lang(session, message.from_user.id)

    binance_file_id = None
    if message.photo:
        binance_file_id = message.photo[-1].file_id
    elif message.text:
        # Accept text as fallback (e.g. if user sends ID instead)
        binance_file_id = f"text:{message.text.strip()}"

    await state.update_data(binance_file_id=binance_file_id)
    await state.set_state(LootFSM.waiting_stake_screenshot)
    await message.answer(
        t(lang, "loot_send_stake"),
        parse_mode="HTML",
        reply_markup=cancel_keyboard(lang, back_cb="loot"),
    )


# ─── Step 3: Receive Stake screenshot → show Roll button ──────────────────────

@router.message(LootFSM.waiting_stake_screenshot, F.photo | F.text)
async def fsm_loot_stake(message: Message, state: FSMContext, session: AsyncSession) -> None:
    lang = await _lang(session, message.from_user.id)

    stake_file_id = None
    if message.photo:
        stake_file_id = message.photo[-1].file_id
    elif message.text:
        stake_file_id = f"text:{message.text.strip()}"

    await state.update_data(stake_file_id=stake_file_id)
    await state.set_state(LootFSM.confirm)
    await message.answer(
        t(lang, "loot_ready"),
        parse_mode="HTML",
        reply_markup=loot_roll_keyboard(lang),
    )


# ─── Step 4: Roll — determine prize ───────────────────────────────────────────

@router.callback_query(LootFSM.confirm, F.data == "loot:roll")
async def cb_loot_roll(call: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    lang = await _lang(session, call.from_user.id)
    user = await repository.get_or_create_user(session, call.from_user.id, call.from_user.username)

    if user.loot_banned:
        await state.clear()
        await call.answer(t(lang, "loot_banned_msg"), show_alert=True)
        return

    # Final cooldown guard (race condition)
    can, remaining = await repository.check_cooldown(
        session, call.from_user.id, "last_loot_at", LOOT_COOLDOWN_HOURS
    )
    if not can:
        await state.clear()
        secs = int(remaining.total_seconds())
        h, m = secs // 3600, (secs % 3600) // 60
        await call.answer(t(lang, "loot_cooldown", h=h, m=m), show_alert=True)
        return

    data            = await state.get_data()
    binance_file_id = data.get("binance_file_id")
    stake_file_id   = data.get("stake_file_id")
    await state.clear()

    prize = _roll_prize()
    await repository.set_timestamp(session, call.from_user.id, "last_loot_at")

    logger.info("Loot roll | telegram_id=%s | prize=$%s", call.from_user.id, prize)

    # Show result to user
    await call.message.edit_text(
        t(lang, "loot_result", prize=prize),
        parse_mode="HTML",
        reply_markup=back_to_menu_keyboard(lang),
    )
    await call.answer()

    # Send to moder group
    if MODER_GROUP_ID:
        pd       = await repository.get_payment_data(session, call.from_user.id)
        uname    = call.from_user.username or "(no username)"
        num      = user.user_number or "—"
        binance  = pd.binance_id if pd and pd.binance_id else "—"
        stake    = pd.stake_user if pd and pd.stake_user else "—"
        header   = t(lang, "loot_moder_header",
                     username=uname, uid=call.from_user.id, num=num,
                     prize=prize, binance=binance, stake=stake)
        try:
            await bot.send_message(MODER_GROUP_ID, header, parse_mode="HTML")

            # Send Binance screenshot
            if binance_file_id:
                if binance_file_id.startswith("text:"):
                    await bot.send_message(MODER_GROUP_ID,
                        f"{t(lang, 'loot_photo_binance')} {binance_file_id[5:]}")
                else:
                    await bot.send_photo(MODER_GROUP_ID, binance_file_id,
                                         caption=t(lang, "loot_photo_binance"))
            else:
                await bot.send_message(MODER_GROUP_ID, t(lang, "loot_no_photo"))

            # Send Stake screenshot
            if stake_file_id:
                if stake_file_id.startswith("text:"):
                    await bot.send_message(MODER_GROUP_ID,
                        f"{t(lang, 'loot_photo_stake')} {stake_file_id[5:]}")
                else:
                    await bot.send_photo(MODER_GROUP_ID, stake_file_id,
                                         caption=t(lang, "loot_photo_stake"))
            else:
                await bot.send_message(MODER_GROUP_ID, t(lang, "loot_no_photo"))

        except Exception as e:
            logger.warning("Loot moder notification failed | %s", e)
