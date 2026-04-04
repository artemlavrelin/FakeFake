import random
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select, update
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
        logger.info("New user registered | telegram_id=%s | username=%s", telegram_id, username)
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
        action = "banned" if banned else "unbanned"
        logger.info("User %s | telegram_id=%s", action, telegram_id)
    return user


async def list_users(session: AsyncSession) -> list[User]:
    result = await session.execute(select(User).order_by(User.created_at))
    return list(result.scalars().all())


# ─── User statistics ──────────────────────────────────────────────────────────

async def get_user_stats(session: AsyncSession, telegram_id: int) -> dict:
    """Return participation count and win count for a user."""
    participations_result = await session.execute(
        select(func.count()).where(ContestParticipant.telegram_id == telegram_id)
    )
    participations = participations_result.scalar() or 0

    wins_result = await session.execute(
        select(func.count()).where(Winner.telegram_id == telegram_id)
    )
    wins = wins_result.scalar() or 0

    return {"participations": participations, "wins": wins}


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
    session: AsyncSession, title: str, prize_text: str, winners_count: int
) -> Contest:
    contest = Contest(
        title=title,
        prize_text=prize_text,
        winners_count=winners_count,
        status="active",
    )
    session.add(contest)
    await session.commit()
    await session.refresh(contest)
    logger.info(
        "Contest created | id=%s | title=%r | winners_count=%s",
        contest.id, title, winners_count,
    )
    return contest


async def get_finished_contests(session: AsyncSession) -> list[Contest]:
    result = await session.execute(
        select(Contest)
        .where(Contest.status == "finished")
        .options(selectinload(Contest.winners).selectinload(Winner.user))
        .order_by(Contest.finished_at.desc())
        .limit(10)
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
    participant = ContestParticipant(contest_id=contest_id, telegram_id=telegram_id)
    session.add(participant)
    await session.commit()
    await session.refresh(participant)
    logger.info(
        "User joined contest | telegram_id=%s | contest_id=%s", telegram_id, contest_id
    )
    return participant


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

async def draw_winners(session: AsyncSession, contest: Contest) -> tuple[list[Winner], int]:
    """
    Randomly select winners, save them, close the contest.

    Fail-safe: if participants < winners_count, use all participants.
    Returns (winners_list, actual_participant_count).
    """
    participants = await get_all_participants(session, contest.id)
    participant_count = len(participants)

    # Fail-safe: never request more winners than participants
    actual_winners_count = min(contest.winners_count, participant_count)

    if actual_winners_count < contest.winners_count:
        logger.warning(
            "Draw fail-safe triggered | contest_id=%s | requested=%s | available=%s → using %s",
            contest.id, contest.winners_count, participant_count, actual_winners_count,
        )

    logger.info(
        "Draw started | contest_id=%s | title=%r | participants=%s | winners_count=%s",
        contest.id, contest.title, participant_count, actual_winners_count,
    )

    chosen = random.sample(participants, actual_winners_count)
    chosen_ids = [p.telegram_id for p in chosen]

    logger.info(
        "Draw winners selected | contest_id=%s | winner_telegram_ids=%s",
        contest.id, chosen_ids,
    )

    for p in chosen:
        session.add(Winner(contest_id=contest.id, telegram_id=p.telegram_id))

    contest.status = "finished"
    contest.finished_at = datetime.utcnow()
    await session.commit()

    # Reload winners with user relation
    result = await session.execute(
        select(Winner)
        .where(Winner.contest_id == contest.id)
        .options(selectinload(Winner.user))
    )
    winners = list(result.scalars().all())

    logger.info(
        "Draw completed | contest_id=%s | title=%r | total_winners=%s",
        contest.id, contest.title, len(winners),
    )
    return winners, participant_count
