"""
/status — admin global stats dashboard
"""
from datetime import datetime

import pytz
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import ADMIN_IDS, BUDAPEST_TZ
from database import repository
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router()


def _admin_only(uid: int) -> bool:
    return uid in ADMIN_IDS


@router.message(Command("status"))
async def cmd_status(message: Message, session: AsyncSession) -> None:
    if not _admin_only(message.from_user.id):
        await message.answer("⛔ Нет доступа"); return

    stats = await repository.get_admin_status_stats(session)
    tz    = pytz.timezone(BUDAPEST_TZ)
    now   = datetime.now(tz).strftime("%H:%M")

    active_r  = 0   # TODO: track active users more granularly
    inactive_r = 0

    text = (
        f"🌍 <b>TOTAL:</b> {stats['total']}      ⌚ <b>TIME:</b> {now}\n\n"
        f"🟩 {stats['verified']}  ⬜️ {stats['pending']}  🟥 {stats['fake']}  ⬛️ {stats['banned_pro']}\n\n"
        f"🔋:{active_r}   🃏:{stats['tasks']}   ❗️:0\n"
        f"🔴:{inactive_r}   👌:{stats['completed']}   🚩:{stats['afk']}\n\n"
        f"⭐️:${stats['earned']:.2f}  💫:${stats['paid_out']:.2f}   🪫:${stats['penalties']:.2f}"
    )
    await message.answer(text, parse_mode="HTML")
