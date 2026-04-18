import random
from datetime import datetime, timedelta, date
from typing import Optional

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import (
    BetPost, Contest, ContestParticipant,
    GlobalSlot, PaymentData, User, UserSlot, Winner,
)
from utils.logger import get_logger

logger = get_logger(__name__)


async def _generate_unique_number(session: AsyncSession) -> int:
    used_r = await session.execute(select(User.user_number).where(User.user_number.isnot(None)))
    used = set(used_r.scalars().all())
    pool = list(set(range(1, 10000)) - used)
    return random.choice(pool) if pool else random.randint(10000, 99999)


# ─── Users ────────────────────────────────────────────────────────────────────

async def get_or_create_user(session: AsyncSession, telegram_id: int, username: Optional[str]) -> User:
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id).options(selectinload(User.payment))
    )
    user = result.scalar_one_or_none()
    if not user:
        number = await _generate_unique_number(session)
        user   = User(telegram_id=telegram_id, username=username, user_number=number, lang="")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.info("New user | telegram_id=%s | number=▫️%s", telegram_id, number)
    else:
        changed = False
        if user.username != username:
            user.username = username
            changed = True
        if user.user_number is None:
            user.user_number = await _generate_unique_number(session)
            changed = True
        if changed:
            await session.commit()
    return user


async def set_lang(session: AsyncSession, telegram_id: int, lang: str) -> Optional[User]:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user   = result.scalar_one_or_none()
    if user:
        user.lang = lang
        await session.commit()
    return user


async def get_user(session: AsyncSession, telegram_id: int) -> Optional[User]:
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id).options(selectinload(User.payment))
    )
    return result.scalar_one_or_none()


async def set_ban(session: AsyncSession, telegram_id: int, banned: bool) -> Optional[User]:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user   = result.scalar_one_or_none()
    if user:
        user.is_banned = banned
        await session.commit()
    return user


async def set_loot_ban(session: AsyncSession, telegram_id: int, banned: bool) -> Optional[User]:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user   = result.scalar_one_or_none()
    if user:
        user.loot_banned = banned
        await session.commit()
    return user


async def list_users(session: AsyncSession) -> list[User]:
    result = await session.execute(
        select(User).options(selectinload(User.payment)).order_by(User.created_at)
    )
    return list(result.scalars().all())


async def get_all_user_ids(session: AsyncSession) -> list[int]:
    result = await session.execute(select(User.telegram_id).where(User.is_banned == False))
    return list(result.scalars().all())


# ─── Cooldowns ────────────────────────────────────────────────────────────────

async def check_cooldown(session: AsyncSession, telegram_id: int, field: str, hours: int) -> tuple[bool, Optional[timedelta]]:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user   = result.scalar_one_or_none()
    if not user:
        return True, None
    last = getattr(user, field, None)
    if not last:
        return True, None
    elapsed  = datetime.utcnow() - last
    cooldown = timedelta(hours=hours)
    if elapsed >= cooldown:
        return True, None
    return False, cooldown - elapsed


async def set_timestamp(session: AsyncSession, telegram_id: int, field: str) -> None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user   = result.scalar_one_or_none()
    if user:
        setattr(user, field, datetime.utcnow())
        await session.commit()


async def check_payment_change_cooldown(session: AsyncSession, telegram_id: int, field: str, days: int) -> tuple[bool, Optional[timedelta]]:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user   = result.scalar_one_or_none()
    if not user:
        return True, None
    last = getattr(user, field, None)
    if not last:
        return True, None
    elapsed  = datetime.utcnow() - last
    cooldown = timedelta(days=days)
    if elapsed >= cooldown:
        return True, None
    return False, cooldown - elapsed


async def set_payment_change_timestamp(session: AsyncSession, telegram_id: int, field: str) -> None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user   = result.scalar_one_or_none()
    if user:
        setattr(user, field, datetime.utcnow())
        await session.commit()


# ─── Stats ────────────────────────────────────────────────────────────────────

async def get_user_stats(session: AsyncSession, telegram_id: int) -> dict:
    part_r  = await session.execute(select(func.count()).where(ContestParticipant.telegram_id == telegram_id))
    wins_r  = await session.execute(select(func.count()).where(Winner.telegram_id == telegram_id))
    prize_r = await session.execute(
        select(func.coalesce(func.sum(Contest.prize_amount), 0))
        .join(Winner, Winner.contest_id == Contest.id)
        .where(Winner.telegram_id == telegram_id)
    )
    last_r  = await session.execute(
        select(Winner.created_at).where(Winner.telegram_id == telegram_id)
        .order_by(Winner.created_at.desc()).limit(1)
    )
    return {
        "participations": part_r.scalar() or 0,
        "wins":           wins_r.scalar() or 0,
        "prize_sum":      float(prize_r.scalar() or 0),
        "last_win":       last_r.scalar_one_or_none(),
    }


async def get_public_stats(session: AsyncSession) -> dict:
    fr = await session.execute(select(func.count()).where(Contest.status == "finished"))
    pr = await session.execute(select(func.count(ContestParticipant.id)))
    wr = await session.execute(select(func.count(Winner.id)))
    sr = await session.execute(
        select(func.coalesce(func.sum(Contest.prize_amount), 0)).where(Contest.status == "finished")
    )
    return {
        "finished_count":     fr.scalar() or 0,
        "total_participants": pr.scalar() or 0,
        "total_winners":      wr.scalar() or 0,
        "total_prize_sum":    float(sr.scalar() or 0),
    }


async def get_top_winners(session: AsyncSession, limit: int = 10) -> list[dict]:
    result = await session.execute(
        select(Winner.telegram_id, func.count(Winner.id).label("wins"))
        .group_by(Winner.telegram_id).order_by(desc("wins")).limit(limit)
    )
    out = []
    for row in result.all():
        ur = await session.execute(select(User).where(User.telegram_id == row.telegram_id))
        u  = ur.scalar_one_or_none()
        out.append({"telegram_id": row.telegram_id, "wins": row.wins,
                    "username": u.username if u else None,
                    "user_number": u.user_number if u else None})
    return out


async def get_top_participants(session: AsyncSession, limit: int = 10) -> list[dict]:
    result = await session.execute(
        select(ContestParticipant.telegram_id, func.count(ContestParticipant.id).label("count"))
        .group_by(ContestParticipant.telegram_id).order_by(desc("count")).limit(limit)
    )
    out = []
    for row in result.all():
        ur = await session.execute(select(User).where(User.telegram_id == row.telegram_id))
        u  = ur.scalar_one_or_none()
        out.append({"telegram_id": row.telegram_id, "count": row.count,
                    "username": u.username if u else None,
                    "user_number": u.user_number if u else None})
    return out


# ─── Contests ─────────────────────────────────────────────────────────────────

async def get_active_contest(session: AsyncSession) -> Optional[Contest]:
    result = await session.execute(
        select(Contest).where(Contest.status == "active")
        .options(selectinload(Contest.participants))
        .order_by(Contest.created_at.desc())
    )
    return result.scalar_one_or_none()


async def create_contest(session: AsyncSession, title: str, prize_text: str,
                         prize_amount: float, winners_count: int) -> Contest:
    contest = Contest(title=title, prize_text=prize_text,
                      prize_amount=prize_amount, winners_count=winners_count, status="active")
    session.add(contest)
    await session.commit()
    await session.refresh(contest)
    logger.info("Contest created | id=%s | title=%r | prize=%s | winners=%s",
                contest.id, title, prize_amount, winners_count)
    return contest


async def edit_contest(session: AsyncSession, contest: Contest, field: str, value) -> Contest:
    setattr(contest, field, value)
    await session.commit()
    await session.refresh(contest)
    return contest


async def cancel_contest(session: AsyncSession, contest: Contest) -> Contest:
    contest.status = "cancelled"
    contest.finished_at = datetime.utcnow()
    await session.commit()
    return contest


async def get_finished_contests(session: AsyncSession, limit: int = 10) -> list[Contest]:
    result = await session.execute(
        select(Contest).where(Contest.status == "finished")
        .options(selectinload(Contest.winners).selectinload(Winner.user))
        .order_by(Contest.finished_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


async def is_participant(session: AsyncSession, contest_id: int, telegram_id: int) -> bool:
    result = await session.execute(
        select(ContestParticipant).where(
            ContestParticipant.contest_id == contest_id,
            ContestParticipant.telegram_id == telegram_id,
        )
    )
    return result.scalar_one_or_none() is not None


async def add_participant(session: AsyncSession, contest_id: int, telegram_id: int) -> ContestParticipant:
    p = ContestParticipant(contest_id=contest_id, telegram_id=telegram_id)
    session.add(p)
    await session.commit()
    await session.refresh(p)
    logger.info("Joined | telegram_id=%s | contest_id=%s", telegram_id, contest_id)
    return p


async def get_participant_count(session: AsyncSession, contest_id: int) -> int:
    result = await session.execute(select(func.count()).where(ContestParticipant.contest_id == contest_id))
    return result.scalar() or 0


async def get_all_participants(session: AsyncSession, contest_id: int) -> list[ContestParticipant]:
    result = await session.execute(select(ContestParticipant).where(ContestParticipant.contest_id == contest_id))
    return list(result.scalars().all())


async def draw_winners(session: AsyncSession, contest: Contest) -> tuple[list[Winner], int]:
    participants = await get_all_participants(session, contest.id)
    total  = len(participants)
    actual = min(contest.winners_count, total)
    if actual < contest.winners_count:
        logger.warning("Fail-safe draw | contest_id=%s | requested=%s | available=%s",
                       contest.id, contest.winners_count, total)
    chosen = random.sample(participants, actual)
    for p in chosen:
        session.add(Winner(contest_id=contest.id, telegram_id=p.telegram_id))
    contest.status = "finished"
    contest.finished_at = datetime.utcnow()
    await session.commit()
    result = await session.execute(
        select(Winner).where(Winner.contest_id == contest.id)
        .options(selectinload(Winner.user).selectinload(User.payment))
    )
    winners = list(result.scalars().all())
    logger.info("Winners | contest_id=%s | ids=%s", contest.id, [w.telegram_id for w in winners])
    return winners, total


# ─── Payment data ─────────────────────────────────────────────────────────────

async def get_payment_data(session: AsyncSession, telegram_id: int) -> Optional[PaymentData]:
    result = await session.execute(select(PaymentData).where(PaymentData.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def upsert_payment_data(session: AsyncSession, telegram_id: int,
                               binance_id: Optional[str] = None,
                               stake_user: Optional[str] = None) -> PaymentData:
    result = await session.execute(select(PaymentData).where(PaymentData.telegram_id == telegram_id))
    pd = result.scalar_one_or_none()
    if not pd:
        pd = PaymentData(telegram_id=telegram_id, binance_id=binance_id, stake_user=stake_user)
        session.add(pd)
    else:
        if binance_id is not None:
            pd.binance_id = binance_id
        if stake_user is not None:
            pd.stake_user = stake_user
        pd.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(pd)
    return pd


async def clear_payment_field(session: AsyncSession, telegram_id: int, field: str) -> None:
    result = await session.execute(select(PaymentData).where(PaymentData.telegram_id == telegram_id))
    pd = result.scalar_one_or_none()
    if pd:
        setattr(pd, field, None)
        pd.updated_at = datetime.utcnow()
        await session.commit()


async def list_payment_data(session: AsyncSession, page: int = 0, page_size: int = 15) -> tuple[list[PaymentData], int]:
    count_r = await session.execute(select(func.count(PaymentData.id)))
    total   = count_r.scalar() or 0
    result  = await session.execute(
        select(PaymentData).options(selectinload(PaymentData.user))
        .order_by(PaymentData.telegram_id).offset(page * page_size).limit(page_size)
    )
    return list(result.scalars().all()), total


# ─── Slot system ──────────────────────────────────────────────────────────────

async def get_or_create_user_slot(
    session: AsyncSession, telegram_id: int, slot_name: str, spins: int
) -> UserSlot:
    result = await session.execute(select(UserSlot).where(UserSlot.telegram_id == telegram_id))
    us = result.scalar_one_or_none()
    today = date.today()
    if not us:
        us = UserSlot(telegram_id=telegram_id, slot_name=slot_name, spins=spins, slot_date=today)
        session.add(us)
        await session.commit()
        await session.refresh(us)
    return us


async def update_user_slot(session: AsyncSession, telegram_id: int, slot_name: str, spins: int) -> UserSlot:
    result = await session.execute(select(UserSlot).where(UserSlot.telegram_id == telegram_id))
    us = result.scalar_one_or_none()
    today = date.today()
    if not us:
        us = UserSlot(telegram_id=telegram_id, slot_name=slot_name, spins=spins, slot_date=today)
        session.add(us)
    else:
        us.slot_name = slot_name
        us.spins     = spins
        us.slot_date = today
    await session.commit()
    await session.refresh(us)
    return us


async def get_user_slot(session: AsyncSession, telegram_id: int) -> Optional[UserSlot]:
    result = await session.execute(select(UserSlot).where(UserSlot.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def get_global_slot(session: AsyncSession) -> Optional[GlobalSlot]:
    result = await session.execute(select(GlobalSlot).limit(1))
    return result.scalar_one_or_none()


async def set_global_slot(session: AsyncSession, slot_name: str) -> GlobalSlot:
    result = await session.execute(select(GlobalSlot).limit(1))
    gs = result.scalar_one_or_none()
    if not gs:
        gs = GlobalSlot(slot_name=slot_name, updated_at=datetime.utcnow())
        session.add(gs)
    else:
        gs.slot_name  = slot_name
        gs.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(gs)
    return gs


async def get_all_user_slot_ids(session: AsyncSession) -> list[int]:
    result = await session.execute(select(UserSlot.telegram_id))
    return list(result.scalars().all())


# ─── Bet posts ────────────────────────────────────────────────────────────────

async def create_bet_post(session: AsyncSession, text: str, admin_id: int,
                           media_id: Optional[str] = None,
                           media_type: Optional[str] = None) -> BetPost:
    bp = BetPost(text=text, media_id=media_id, media_type=media_type, admin_id=admin_id)
    session.add(bp)
    await session.commit()
    await session.refresh(bp)
    logger.info("Bet post created | id=%s | admin=%s", bp.id, admin_id)
    return bp


async def list_bet_posts(session: AsyncSession, limit: int = 20) -> list[BetPost]:
    result = await session.execute(
        select(BetPost).order_by(BetPost.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())
