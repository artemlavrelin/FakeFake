import random
from datetime import datetime
from typing import Optional

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import (
    BonusWinner, Contest, ContestParticipant,
    PaymentData, User, Winner,
)
from utils.logger import get_logger

logger = get_logger(__name__)

# ─── User number pool ─────────────────────────────────────────────────────────

async def _generate_unique_number(session: AsyncSession) -> int:
    """Pick a random unused number in [1, 9999]."""
    used_result = await session.execute(
        select(User.user_number).where(User.user_number.isnot(None))
    )
    used = set(used_result.scalars().all())
    pool = list(set(range(1, 10000)) - used)
    if not pool:
        # All numbers taken — extend range gracefully
        return random.randint(10000, 99999)
    return random.choice(pool)


# ─── Users ────────────────────────────────────────────────────────────────────

async def get_or_create_user(
    session: AsyncSession, telegram_id: int, username: Optional[str]
) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        number = await _generate_unique_number(session)
        user = User(telegram_id=telegram_id, username=username, user_number=number)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.info(
            "New user | telegram_id=%s | username=%s | number=%s",
            telegram_id, username, number,
        )
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


async def get_user(session: AsyncSession, telegram_id: int) -> Optional[User]:
    result = await session.execute(
        select(User)
        .where(User.telegram_id == telegram_id)
        .options(selectinload(User.payment))
    )
    return result.scalar_one_or_none()


async def set_ban(session: AsyncSession, telegram_id: int, banned: bool) -> Optional[User]:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user:
        user.is_banned = banned
        await session.commit()
        logger.info("User %s | telegram_id=%s", "banned" if banned else "unbanned", telegram_id)
    return user


async def list_users(session: AsyncSession) -> list[User]:
    result = await session.execute(
        select(User).options(selectinload(User.payment)).order_by(User.created_at)
    )
    return list(result.scalars().all())


async def get_all_user_ids(session: AsyncSession) -> list[int]:
    result = await session.execute(
        select(User.telegram_id).where(User.is_banned == False)
    )
    return list(result.scalars().all())


# ─── User statistics ──────────────────────────────────────────────────────────

async def get_user_stats(session: AsyncSession, telegram_id: int) -> dict:
    part_r = await session.execute(
        select(func.count()).where(ContestParticipant.telegram_id == telegram_id)
    )
    participations: int = part_r.scalar() or 0

    wins_r = await session.execute(
        select(func.count()).where(Winner.telegram_id == telegram_id)
    )
    wins: int = wins_r.scalar() or 0

    prize_r = await session.execute(
        select(func.coalesce(func.sum(Contest.prize_amount), 0))
        .join(Winner, Winner.contest_id == Contest.id)
        .where(Winner.telegram_id == telegram_id)
    )
    prize_sum: float = float(prize_r.scalar() or 0)

    last_win_r = await session.execute(
        select(Winner.created_at)
        .where(Winner.telegram_id == telegram_id)
        .order_by(Winner.created_at.desc())
        .limit(1)
    )
    last_win = last_win_r.scalar_one_or_none()

    return {
        "participations": participations,
        "wins": wins,
        "prize_sum": prize_sum,
        "last_win": last_win,
    }


# ─── Public statistics ────────────────────────────────────────────────────────

async def get_public_stats(session: AsyncSession) -> dict:
    finished_r = await session.execute(
        select(func.count()).where(Contest.status == "finished")
    )
    parts_r = await session.execute(select(func.count(ContestParticipant.id)))
    wins_r = await session.execute(select(func.count(Winner.id)))
    prize_r = await session.execute(
        select(func.coalesce(func.sum(Contest.prize_amount), 0))
        .where(Contest.status == "finished")
    )
    return {
        "finished_count": finished_r.scalar() or 0,
        "total_participants": parts_r.scalar() or 0,
        "total_winners": wins_r.scalar() or 0,
        "total_prize_sum": float(prize_r.scalar() or 0),
    }


# ─── Top lists ────────────────────────────────────────────────────────────────

async def _enrich_rows(session, rows, id_field: str) -> list[dict]:
    out = []
    for row in rows:
        tid = getattr(row, id_field)
        ur = await session.execute(
            select(User).where(User.telegram_id == tid).options(selectinload(User.payment))
        )
        user = ur.scalar_one_or_none()
        out.append({
            "telegram_id": tid,
            "wins": getattr(row, "wins", None),
            "count": getattr(row, "count", None),
            "username": user.username if user else None,
            "user_number": user.user_number if user else None,
        })
    return out


async def get_top_winners(session: AsyncSession, limit: int = 10) -> list[dict]:
    result = await session.execute(
        select(Winner.telegram_id, func.count(Winner.id).label("wins"))
        .group_by(Winner.telegram_id)
        .order_by(desc("wins"))
        .limit(limit)
    )
    return await _enrich_rows(session, result.all(), "telegram_id")


async def get_top_participants(session: AsyncSession, limit: int = 10) -> list[dict]:
    result = await session.execute(
        select(ContestParticipant.telegram_id, func.count(ContestParticipant.id).label("count"))
        .group_by(ContestParticipant.telegram_id)
        .order_by(desc("count"))
        .limit(limit)
    )
    return await _enrich_rows(session, result.all(), "telegram_id")


# ─── Contests ─────────────────────────────────────────────────────────────────

async def get_active_contest(session: AsyncSession) -> Optional[Contest]:
    result = await session.execute(
        select(Contest)
        .where(Contest.status == "active")
        .options(selectinload(Contest.participants))
        .order_by(Contest.created_at.desc())
    )
    return result.scalar_one_or_none()


async def get_contest_by_id(session: AsyncSession, contest_id: int) -> Optional[Contest]:
    result = await session.execute(
        select(Contest)
        .where(Contest.id == contest_id)
        .options(
            selectinload(Contest.participants),
            selectinload(Contest.winners).selectinload(Winner.user),
        )
    )
    return result.scalar_one_or_none()


async def create_contest(
    session: AsyncSession, title: str, prize_text: str,
    prize_amount: float, winners_count: int,
) -> Contest:
    contest = Contest(
        title=title, prize_text=prize_text,
        prize_amount=prize_amount, winners_count=winners_count, status="active",
    )
    session.add(contest)
    await session.commit()
    await session.refresh(contest)
    logger.info(
        "Contest created | id=%s | title=%r | prize=%s | winners=%s",
        contest.id, title, prize_amount, winners_count,
    )
    return contest


async def edit_contest(
    session: AsyncSession, contest: Contest, field: str, value
) -> Contest:
    setattr(contest, field, value)
    await session.commit()
    await session.refresh(contest)
    logger.info("Contest edited | id=%s | field=%s | value=%r", contest.id, field, value)
    return contest


async def cancel_contest(session: AsyncSession, contest: Contest) -> Contest:
    contest.status = "cancelled"
    contest.finished_at = datetime.utcnow()
    await session.commit()
    logger.info("Contest cancelled | id=%s", contest.id)
    return contest


async def get_finished_contests(session: AsyncSession, limit: int = 10) -> list[Contest]:
    result = await session.execute(
        select(Contest)
        .where(Contest.status == "finished")
        .options(selectinload(Contest.winners).selectinload(Winner.user))
        .order_by(Contest.finished_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


# ─── Participants ─────────────────────────────────────────────────────────────

async def is_participant(session: AsyncSession, contest_id: int, telegram_id: int) -> bool:
    result = await session.execute(
        select(ContestParticipant).where(
            ContestParticipant.contest_id == contest_id,
            ContestParticipant.telegram_id == telegram_id,
        )
    )
    return result.scalar_one_or_none() is not None


async def add_participant(
    session: AsyncSession, contest_id: int, telegram_id: int
) -> ContestParticipant:
    p = ContestParticipant(contest_id=contest_id, telegram_id=telegram_id)
    session.add(p)
    await session.commit()
    await session.refresh(p)
    logger.info("Joined | telegram_id=%s | contest_id=%s", telegram_id, contest_id)
    return p


async def get_participant_count(session: AsyncSession, contest_id: int) -> int:
    result = await session.execute(
        select(func.count()).where(ContestParticipant.contest_id == contest_id)
    )
    return result.scalar() or 0


async def get_all_participants(
    session: AsyncSession, contest_id: int
) -> list[ContestParticipant]:
    result = await session.execute(
        select(ContestParticipant).where(ContestParticipant.contest_id == contest_id)
    )
    return list(result.scalars().all())


# ─── Draw ─────────────────────────────────────────────────────────────────────

async def draw_winners(
    session: AsyncSession, contest: Contest
) -> tuple[list[Winner], int]:
    participants = await get_all_participants(session, contest.id)
    total = len(participants)
    actual = min(contest.winners_count, total)

    if actual < contest.winners_count:
        logger.warning(
            "Fail-safe draw | contest_id=%s | requested=%s | available=%s",
            contest.id, contest.winners_count, total,
        )

    logger.info(
        "Draw | contest_id=%s | participants=%s | winners=%s",
        contest.id, total, actual,
    )

    chosen = random.sample(participants, actual)
    for p in chosen:
        session.add(Winner(contest_id=contest.id, telegram_id=p.telegram_id))

    contest.status = "finished"
    contest.finished_at = datetime.utcnow()
    await session.commit()

    result = await session.execute(
        select(Winner)
        .where(Winner.contest_id == contest.id)
        .options(selectinload(Winner.user).selectinload(User.payment))
    )
    winners = list(result.scalars().all())
    logger.info("Winners | contest_id=%s | ids=%s", contest.id, [w.telegram_id for w in winners])
    return winners, total


# ─── Bonus draw ───────────────────────────────────────────────────────────────

async def bonus_draw(
    session: AsyncSession,
    contest_id: int,
    count: int,
    exclude_previous_winners: bool = False,
    note: str = "",
) -> list[BonusWinner]:
    """
    Randomly pick `count` participants from a contest for a bonus prize.
    Optionally exclude users who already won (main or bonus) in this contest.
    """
    participants = await get_all_participants(session, contest_id)
    if not participants:
        return []

    exclude_ids: set[int] = set()
    if exclude_previous_winners:
        win_r = await session.execute(
            select(Winner.telegram_id).where(Winner.contest_id == contest_id)
        )
        bonus_r = await session.execute(
            select(BonusWinner.telegram_id).where(BonusWinner.contest_id == contest_id)
        )
        exclude_ids = set(win_r.scalars().all()) | set(bonus_r.scalars().all())

    eligible = [p for p in participants if p.telegram_id not in exclude_ids]
    if not eligible:
        return []

    actual = min(count, len(eligible))
    chosen = random.sample(eligible, actual)

    bonus_winners: list[BonusWinner] = []
    for p in chosen:
        bw = BonusWinner(contest_id=contest_id, telegram_id=p.telegram_id, note=note)
        session.add(bw)
        bonus_winners.append(bw)

    await session.commit()

    # Reload with user + payment
    result = await session.execute(
        select(BonusWinner)
        .where(
            BonusWinner.contest_id == contest_id,
            BonusWinner.created_at >= bonus_winners[0].created_at,
        )
        .options(selectinload(BonusWinner.user).selectinload(User.payment))
    )
    loaded = list(result.scalars().all())

    logger.info(
        "Bonus draw | contest_id=%s | count=%s | exclude_prev=%s | winners=%s",
        contest_id, actual, exclude_previous_winners,
        [bw.telegram_id for bw in loaded],
    )
    return loaded


# ─── Payment data ─────────────────────────────────────────────────────────────

async def get_payment_data(
    session: AsyncSession, telegram_id: int
) -> Optional[PaymentData]:
    result = await session.execute(
        select(PaymentData).where(PaymentData.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def upsert_payment_data(
    session: AsyncSession,
    telegram_id: int,
    binance_id: Optional[str] = None,
    stake_id: Optional[str] = None,
) -> PaymentData:
    """Create or update payment record. Only provided fields are updated."""
    result = await session.execute(
        select(PaymentData).where(PaymentData.telegram_id == telegram_id)
    )
    pd = result.scalar_one_or_none()
    if not pd:
        pd = PaymentData(
            telegram_id=telegram_id,
            binance_id=binance_id,
            stake_id=stake_id,
        )
        session.add(pd)
    else:
        if binance_id is not None:
            pd.binance_id = binance_id
        if stake_id is not None:
            pd.stake_id = stake_id
        pd.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(pd)
    logger.info(
        "Payment data saved | telegram_id=%s | binance=%s | stake=%s",
        telegram_id,
        bool(pd.binance_id),
        bool(pd.stake_id),
    )
    return pd


async def admin_set_payment(
    session: AsyncSession,
    telegram_id: int,
    binance_id: Optional[str],
    stake_id: Optional[str],
) -> PaymentData:
    return await upsert_payment_data(session, telegram_id, binance_id, stake_id)


async def list_payment_data(
    session: AsyncSession, page: int = 0, page_size: int = 20
) -> tuple[list[PaymentData], int]:
    count_r = await session.execute(select(func.count(PaymentData.id)))
    total = count_r.scalar() or 0
    result = await session.execute(
        select(PaymentData)
        .options(selectinload(PaymentData.user))
        .order_by(PaymentData.telegram_id)
        .offset(page * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total
