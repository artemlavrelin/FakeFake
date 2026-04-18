"""
APScheduler job: runs at 00:00 Europe/Budapest every day.
- Picks a new global slot of the day
- Assigns fresh personal slots + spins to all users who have played /slot before
"""
import random
import logging
from datetime import date

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import BUDAPEST_TZ, SLOT_SPINS_MAX, SLOT_SPINS_MIN
from data.slots import SLOTS
from database import repository
from database.engine import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def _daily_slot_update() -> None:
    logger.info("Daily slot update started")
    async with AsyncSessionLocal() as session:
        # 1. New global slot of the day
        global_slot = random.choice(SLOTS)
        await repository.set_global_slot(session, global_slot)
        logger.info("Global slot of the day: %s", global_slot)

        # 2. Update all users who already have a slot record
        user_ids = await repository.get_all_user_slot_ids(session)
        updated  = 0
        for tid in user_ids:
            slot  = random.choice(SLOTS)
            spins = random.randint(SLOT_SPINS_MIN, SLOT_SPINS_MAX)
            await repository.update_user_slot(session, tid, slot, spins)
            updated += 1

        logger.info("Daily slots updated | users=%s | global_slot=%s", updated, global_slot)


def create_scheduler() -> AsyncIOScheduler:
    tz        = pytz.timezone(BUDAPEST_TZ)
    scheduler = AsyncIOScheduler(timezone=tz)
    scheduler.add_job(
        _daily_slot_update,
        trigger="cron",
        hour=0,
        minute=0,
        timezone=tz,
        id="daily_slot_update",
        replace_existing=True,
    )
    return scheduler
