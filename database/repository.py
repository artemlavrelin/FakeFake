import random
from datetime import datetime
from typing import Optional

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import Contest, ContestParticipant, User, Winner
from utils.logger import get_logger

logger = get_logger(__name__)


# ─── Users ────────────────────────────────────────────────────────────────────

async def get_or_create_user(
    session: AsyncSession, telegram_id: int, username: Optional[str]
) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(telegram_id=telegram_id, username=username)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.info("New user | telegram_id=%s | username=%s", telegram_id, username)
    else:
        if user.username != username:
            user.username = username
            await session.commit()
    return user


async def get_user(session: AsyncSession, telegram_id: int) -> Optional[User]:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
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
    result = await session.execute(select(User).order_by(User.created_at))
    return list(result.scalars().all())


async def get_all_user_ids(session: AsyncSession) -> list[int]:
    """Return all non-banned telegram_ids for broadcast."""
    result = await session.execute(
        select(User.telegram_id).where(User.is_banned == False)
    )
    return list(result.scalars().all())


# ─── User statistics ──────────────────────────────────────────────────────────

async def get_user_stats(session: AsyncSession, telegram_id: int) -> dict:
    part_result = await session.execute(
        select(func.count()).where(ContestParticipant.telegram_id == telegram_id)
    )
    participations: int = part_result.scalar() or 0

    wins_result = await session.execute(
        select(func.count()).where(Winner.telegram_id == telegram_id)
    )
    wins: int = wins_result.scalar() or 0

    # Sum prize_amount of won contests
    prize_sum_result = await session.execute(
        select(func.coalesce(func.sum(Contest.prize_amount), 0))
        .join(Winner, Winner.contest_id == Contest.id)
        .where(Winner.telegram_id == telegram_id)
    )
    prize_sum: float = float(prize_sum_result.scalar() or 0)

    # Last win date
    last_win_result = await session.execute(
        select(Winner.created_at)
        .where(Winner.telegram_id == telegram_id)
        .order_by(Winner.created_at.desc())
        .limit(1)
    )
    last_win = last_win_result.scalar_one_or_none()

    return {
        "participations": participations,
        "wins": wins,
        "prize_sum": prize_sum,
        "last_win": last_win,
    }


# ─── Public statistics ────────────────────────────────────────────────────────

async def get_public_stats(session: AsyncSession) -> dict:
    finished_result = await session.execute(
        select(func.count()).where(Contest.status == "finished")
    )
    finished_count: int = finished_result.scalar() or 0

    participants_result = await session.execute(select(func.count(ContestParticipant.id)))
    total_participants: int = participants_result.scalar() or 0

    winners_result = await session.execute(select(func.count(Winner.id)))
    total_winners: int = winners_result.scalar() or 0

    prize_sum_result = await session.execute(
        select(func.coalesce(func.sum(Contest.prize_amount), 0))
        .where(Contest.status == "finished")
    )
    total_prize_sum: float = float(prize_sum_result.scalar() or 0)

    return {
        "finished_count": finished_count,
        "total_participants": total_participants,
        "total_winners": total_winners,
        "total_prize_sum": total_prize_sum,
    }


# ─── Top lists ────────────────────────────────────────────────────────────────

async def get_top_winners(session: AsyncSession, limit: int = 10) -> list[dict]:
    result = await session.execute(
        select(Winner.telegram_id, func.count(Winner.id).label("wins"))
        .group_by(Winner.telegram_id)
        .order_by(desc("wins"))
        .limit(limit)
    )
    rows = result.all()
    out = []
    for row in rows:
        user_r = await session.execute(select(User).where(User.telegram_id == row.telegram_id))
        user = user_r.scalar_one_or_none()
        out.append({"telegram_id": row.telegram_id, "wins": row.wins, "username": user.username if user else None})
    return out


async def get_top_participants(session: AsyncSession, limit: int = 10) -> list[dict]:
    result = await session.execute(
        select(ContestParticipant.telegram_id, func.count(ContestParticipant.id).label("count"))
        .group_by(ContestParticipant.telegram_id)
        .order_by(desc("count"))
        .limit(limit)
    )
    rows = result.all()
    out = []
    for row in rows:
        user_r = await session.execute(select(User).where(User.telegram_id == row.telegram_id))
        user = user_r.scalar_one_or_none()
        out.append({"telegram_id": row.telegram_id, "count": row.count, "username": user.username if user else None})
    return out


# ─── Contests ─────────────────────────────────────────────────────────────────

async def get_active_contest(session: AsyncSession) -> Optional[Contest]:
    result = await session.execute(
        select(Contest)
        .where(Contest.status == "active")
        .options(selectinload(Contest.participants))
        .order_by(Contest.created_at.desc())
    )
    return result.scalar_one_or_none()


async def create_contest(
    session: AsyncSession,
    title: str,
    prize_text: str,
    prize_amount: float,
    winners_count: int,
) -> Contest:
    contest = Contest(
        title=title,
        prize_text=prize_text,
        prize_amount=prize_amount,
        winners_count=winners_count,
        status="active",
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
    session: AsyncSession,
    contest: Contest,
    field: str,
    value: str | float | int,
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
    logger.info("Contest cancelled | id=%s | title=%r", contest.id, contest.title)
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


# ─── Participants ──────────────────────────────────────────────────────────────

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
    logger.info("Joined contest | telegram_id=%s | contest_id=%s", telegram_id, contest_id)
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

    actual_count = min(contest.winners_count, total)
    if actual_count < contest.winners_count:
        logger.warning(
            "Fail-safe | contest_id=%s | requested=%s | available=%s",
            contest.id, contest.winners_count, total,
        )

    logger.info(
        "Draw started | contest_id=%s | title=%r | participants=%s | winners=%s",
        contest.id, contest.title, total, actual_count,
    )

    chosen = random.sample(participants, actual_count)
    for p in chosen:
        session.add(Winner(contest_id=contest.id, telegram_id=p.telegram_id))

    contest.status = "finished"
    contest.finished_at = datetime.utcnow()
    await session.commit()

    result = await session.execute(
        select(Winner)
        .where(Winner.contest_id == contest.id)
        .options(selectinload(Winner.user))
    )
    winners = list(result.scalars().all())

    logger.info(
        "Draw done | contest_id=%s | winners=%s",
        contest.id, [w.telegram_id for w in winners],
    )
    return winners, total
