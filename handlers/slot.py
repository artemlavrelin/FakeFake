"""
/slot — show user's personal daily slot and the global slot of the day.
"""
import random
from datetime import date

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import SLOT_SPINS_MAX, SLOT_SPINS_MIN
from data.slots import SLOTS
from database import repository
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router()


async def _assign_slot_if_needed(session: AsyncSession, telegram_id: int) -> tuple[str, int, str]:
    """
    Ensure user has a slot for today.
    Returns (user_slot_name, spins, global_slot_name).
    """
    global_gs = await repository.get_global_slot(session)
    if not global_gs or not global_gs.slot_name:
        # No global slot yet — pick one
        global_slot = random.choice(SLOTS)
        await repository.set_global_slot(session, global_slot)
    else:
        global_slot = global_gs.slot_name

    us = await repository.get_user_slot(session, telegram_id)
    today = date.today()

    if us and us.slot_date == today and us.slot_name:
        # Already assigned today
        return us.slot_name, us.spins, global_slot

    # Assign new slot for today
    user_slot = random.choice(SLOTS)
    spins     = random.randint(SLOT_SPINS_MIN, SLOT_SPINS_MAX)
    await repository.update_user_slot(session, telegram_id, user_slot, spins)
    logger.info("Slot assigned | telegram_id=%s | slot=%s | spins=%s", telegram_id, user_slot, spins)
    return user_slot, spins, global_slot


@router.message(Command("slot"))
async def cmd_slot(message: Message, session: AsyncSession) -> None:
    await repository.get_or_create_user(session, message.from_user.id, message.from_user.username)

    user_slot, spins, global_slot = await _assign_slot_if_needed(session, message.from_user.id)

    await message.answer(
        f"🎰 <b>Твой слот:</b>\n\n"
        f"<b>{user_slot}</b>\n\n"
        f"🔁 Спины: <b>{spins}</b>\n\n"
        f"🎯 <b>Слот дня:</b>\n"
        f"<b>{global_slot}</b>",
        parse_mode="HTML",
    )
