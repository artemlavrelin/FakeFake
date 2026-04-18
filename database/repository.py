import random
from datetime import datetime, timedelta, date
from typing import Optional

from sqlalchemy import desc, func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import (
    BetPost, Contest, ContestParticipant, GlobalSlot,
    PaymentData, Task, TaskComment, TaskLog,
    User, UserBalance, UserProfile, UserSlot, Winner, WithdrawalRequest,
)
from utils.logger import get_logger

logger = get_logger(__name__)


# ─── Unique number ────────────────────────────────────────────────────────────

async def _generate_unique_number(session: AsyncSession) -> int:
    used_r = await session.execute(select(User.user_number).where(User.user_number.isnot(None)))
    used = set(used_r.scalars().all())
    pool = list(set(range(1, 10000)) - used)
    return random.choice(pool) if pool else random.randint(10000, 99999)


# ─── Users ────────────────────────────────────────────────────────────────────

async def get_or_create_user(session: AsyncSession, telegram_id: int, username: Optional[str]) -> User:
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
        .options(selectinload(User.payment), selectinload(User.profile), selectinload(User.balance))
    )
    user = result.scalar_one_or_none()
    if not user:
        number = await _generate_unique_number(session)
        user   = User(telegram_id=telegram_id, username=username, user_number=number, lang="")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.info("New user | telegram_id=%s | number=%s", telegram_id, number)
    else:
        changed = False
        if user.username != username:
            user.username = username; changed = True
        if user.user_number is None:
            user.user_number = await _generate_unique_number(session); changed = True
        if changed:
            await session.commit()
    return user


async def get_user(session: AsyncSession, telegram_id: int) -> Optional[User]:
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
        .options(selectinload(User.payment), selectinload(User.profile), selectinload(User.balance))
    )
    return result.scalar_one_or_none()


async def get_user_by_username(session: AsyncSession, username: str) -> Optional[User]:
    clean = username.lstrip("@")
    result = await session.execute(select(User).where(User.username == clean)
        .options(selectinload(User.payment), selectinload(User.profile), selectinload(User.balance)))
    return result.scalar_one_or_none()


async def set_lang(session: AsyncSession, telegram_id: int, lang: str) -> Optional[User]:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user   = result.scalar_one_or_none()
    if user:
        user.lang = lang
        await session.commit()
    return user


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


async def set_afk(session: AsyncSession, telegram_id: int, afk: bool) -> None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user   = result.scalar_one_or_none()
    if user:
        user.is_afk   = afk
        user.afk_since = datetime.utcnow() if afk else None
        await session.commit()


async def delete_user_completely(session: AsyncSession, telegram_id: int) -> bool:
    user = await get_user(session, telegram_id)
    if not user:
        return False
    await session.delete(user)
    await session.commit()
    logger.info("User deleted | telegram_id=%s", telegram_id)
    return True


async def list_users(session: AsyncSession) -> list[User]:
    result = await session.execute(
        select(User).options(selectinload(User.payment), selectinload(User.balance))
        .order_by(User.created_at)
    )
    return list(result.scalars().all())


async def get_all_user_ids(session: AsyncSession) -> list[int]:
    result = await session.execute(select(User.telegram_id).where(User.is_banned == False))
    return list(result.scalars().all())


async def get_afk_users(session: AsyncSession) -> list[User]:
    result = await session.execute(select(User).where(User.is_afk == True))
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


# ─── Profile ──────────────────────────────────────────────────────────────────

async def get_or_create_profile(session: AsyncSession, telegram_id: int) -> UserProfile:
    result = await session.execute(select(UserProfile).where(UserProfile.telegram_id == telegram_id))
    p = result.scalar_one_or_none()
    if not p:
        p = UserProfile(telegram_id=telegram_id)
        session.add(p)
        await session.commit()
        await session.refresh(p)
    return p


async def save_profile(session: AsyncSession, telegram_id: int,
                        instagram: str, threads: str, facebook: str, twitter: str) -> UserProfile:
    p = await get_or_create_profile(session, telegram_id)
    p.instagram  = instagram
    p.threads    = threads
    p.facebook   = facebook
    p.twitter    = twitter
    p.status     = "pending"
    p.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(p)

    # Calculate bonus
    filled = sum(1 for v in [instagram, threads, facebook, twitter] if v and v.strip())
    bonus  = round(filled * 0.10, 2)
    if bonus > 0 and not p.bonus_paid:
        p.bonus_paid = True
        await session.commit()
        await add_balance(session, telegram_id, bonus)
    return p


async def set_profile_status(session: AsyncSession, telegram_id: int, status: str) -> Optional[UserProfile]:
    result = await session.execute(select(UserProfile).where(UserProfile.telegram_id == telegram_id))
    p = result.scalar_one_or_none()
    if p:
        p.status = status
        await session.commit()
    return p


async def admin_update_profile(session: AsyncSession, telegram_id: int, **kwargs) -> Optional[UserProfile]:
    result = await session.execute(select(UserProfile).where(UserProfile.telegram_id == telegram_id))
    p = result.scalar_one_or_none()
    if p:
        for k, v in kwargs.items():
            if hasattr(p, k):
                setattr(p, k, v)
        p.updated_at = datetime.utcnow()
        await session.commit()
    return p


# ─── Balance ──────────────────────────────────────────────────────────────────

async def get_or_create_balance(session: AsyncSession, telegram_id: int) -> UserBalance:
    result = await session.execute(select(UserBalance).where(UserBalance.telegram_id == telegram_id))
    b = result.scalar_one_or_none()
    if not b:
        b = UserBalance(telegram_id=telegram_id)
        session.add(b)
        await session.commit()
        await session.refresh(b)
    return b


async def add_balance(session: AsyncSession, telegram_id: int, amount: float) -> UserBalance:
    b = await get_or_create_balance(session, telegram_id)
    b.balance  = round(b.balance + amount, 4)
    b.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(b)
    return b


async def subtract_balance(session: AsyncSession, telegram_id: int, amount: float) -> UserBalance:
    b = await get_or_create_balance(session, telegram_id)
    b.balance  = round(max(0, b.balance - amount), 4)
    b.paid_out = round(b.paid_out + amount, 4)
    b.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(b)
    return b


async def add_penalty(session: AsyncSession, telegram_id: int, amount: float) -> UserBalance:
    b = await get_or_create_balance(session, telegram_id)
    b.penalties = round(b.penalties + amount, 4)
    b.balance   = round(max(0, b.balance - amount), 4)
    b.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(b)
    return b


async def top_balances(session: AsyncSession, limit: int = 10) -> list[tuple]:
    result = await session.execute(
        select(UserBalance, User)
        .join(User, User.telegram_id == UserBalance.telegram_id)
        .order_by(UserBalance.balance.desc())
        .limit(limit)
    )
    return result.all()


# ─── Withdrawals ──────────────────────────────────────────────────────────────

async def create_withdrawal(session: AsyncSession, telegram_id: int, amount: float) -> WithdrawalRequest:
    w = WithdrawalRequest(telegram_id=telegram_id, amount=amount)
    session.add(w)
    await session.commit()
    await session.refresh(w)
    return w


async def update_withdrawal(session: AsyncSession, withdrawal_id: int,
                              status: str, moder_msg_id: int = None) -> Optional[WithdrawalRequest]:
    result = await session.execute(select(WithdrawalRequest).where(WithdrawalRequest.id == withdrawal_id))
    w = result.scalar_one_or_none()
    if w:
        w.status      = status
        w.resolved_at = datetime.utcnow()
        if moder_msg_id:
            w.moder_msg_id = moder_msg_id
        await session.commit()
    return w


async def get_withdrawal(session: AsyncSession, withdrawal_id: int) -> Optional[WithdrawalRequest]:
    result = await session.execute(select(WithdrawalRequest).where(WithdrawalRequest.id == withdrawal_id))
    return result.scalar_one_or_none()


# ─── Tasks ────────────────────────────────────────────────────────────────────

async def create_task(session: AsyncSession, platform: str, link: str, max_users: int,
                       action_type: str, description: str, reward: float, admin_id: int) -> Task:
    t = Task(platform=platform, link=link, max_users=max_users,
             action_type=action_type, description=description, reward=reward, admin_id=admin_id)
    session.add(t)
    await session.commit()
    await session.refresh(t)
    logger.info("Task created | id=%s | platform=%s | reward=%s", t.id, platform, reward)
    return t


async def add_task_comments(session: AsyncSession, task_id: int, comments: list[str]) -> None:
    for text in comments:
        session.add(TaskComment(task_id=task_id, text=text.strip()))
    await session.commit()


async def get_task(session: AsyncSession, task_id: int) -> Optional[Task]:
    result = await session.execute(
        select(Task).where(Task.id == task_id)
        .options(selectinload(Task.comments), selectinload(Task.logs))
    )
    return result.scalar_one_or_none()


async def delete_task(session: AsyncSession, task_id: int) -> bool:
    task = await get_task(session, task_id)
    if not task:
        return False
    task.is_active = False
    await session.commit()
    return True


async def get_random_available_task(session: AsyncSession, telegram_id: int) -> Optional[Task]:
    """Get a random active task the user hasn't taken."""
    taken_r = await session.execute(
        select(TaskLog.task_id).where(TaskLog.telegram_id == telegram_id)
    )
    taken_ids = set(taken_r.scalars().all())

    avail_r = await session.execute(
        select(Task).where(
            and_(
                Task.is_active == True,
            )
        ).options(selectinload(Task.logs))
    )
    all_tasks = avail_r.scalars().all()

    eligible = []
    for task in all_tasks:
        if task.id in taken_ids:
            continue
        completed = sum(1 for l in task.logs if l.status == "completed")
        if completed < task.max_users:
            eligible.append(task)

    return random.choice(eligible) if eligible else None


async def accept_task(session: AsyncSession, task_id: int, telegram_id: int) -> Optional[TaskLog]:
    # Assign unused comment if task requires it
    comm_r = await session.execute(
        select(TaskComment).where(
            and_(TaskComment.task_id == task_id, TaskComment.is_used == False)
        ).limit(1)
    )
    comment = comm_r.scalar_one_or_none()
    comment_id = None
    if comment:
        comment.is_used = True
        comment.used_by = telegram_id
        comment_id      = comment.id

    expires = datetime.utcnow() + timedelta(minutes=60)
    tl = TaskLog(task_id=task_id, telegram_id=telegram_id,
                 comment_id=comment_id, status="accepted", expires_at=expires)
    session.add(tl)
    await session.commit()
    await session.refresh(tl)
    logger.info("Task accepted | task_id=%s | telegram_id=%s", task_id, telegram_id)
    return tl


async def get_active_task_log(session: AsyncSession, telegram_id: int) -> Optional[TaskLog]:
    result = await session.execute(
        select(TaskLog).where(
            and_(TaskLog.telegram_id == telegram_id,
                 TaskLog.status.in_(["accepted", "pending_review"]))
        ).options(selectinload(TaskLog.task))
        .order_by(TaskLog.accepted_at.desc()).limit(1)
    )
    return result.scalar_one_or_none()


async def update_task_log(session: AsyncSession, log_id: int, status: str,
                           moder_msg_id: int = None) -> Optional[TaskLog]:
    result = await session.execute(select(TaskLog).where(TaskLog.id == log_id))
    tl = result.scalar_one_or_none()
    if tl:
        tl.status = status
        if moder_msg_id:
            tl.moder_msg_id = moder_msg_id
        await session.commit()
    return tl


async def get_task_log_by_id(session: AsyncSession, log_id: int) -> Optional[TaskLog]:
    result = await session.execute(
        select(TaskLog).where(TaskLog.id == log_id)
        .options(selectinload(TaskLog.task), selectinload(TaskLog.user))
    )
    return result.scalar_one_or_none()


async def release_task_comment(session: AsyncSession, comment_id: int) -> None:
    result = await session.execute(select(TaskComment).where(TaskComment.id == comment_id))
    c = result.scalar_one_or_none()
    if c:
        c.is_used = False
        c.used_by = None
        await session.commit()


async def get_task_info(session: AsyncSession, task_id: int) -> dict:
    task = await get_task(session, task_id)
    if not task:
        return {}
    completed = [l for l in task.logs if l.status == "completed"]
    in_progress = [l for l in task.logs if l.status in ("accepted", "pending_review")]
    return {
        "task": task,
        "completed": len(completed),
        "in_progress": len(in_progress),
        "logs": task.logs,
    }


async def list_active_tasks(session: AsyncSession) -> list[Task]:
    result = await session.execute(
        select(Task).where(Task.is_active == True)
        .options(selectinload(Task.logs))
        .order_by(Task.id)
    )
    return list(result.scalars().all())


# ─── User stats ───────────────────────────────────────────────────────────────

async def get_user_stats(session: AsyncSession, telegram_id: int) -> dict:
    part_r = await session.execute(select(func.count()).where(ContestParticipant.telegram_id == telegram_id))
    wins_r = await session.execute(select(func.count()).where(Winner.telegram_id == telegram_id))
    prize_r = await session.execute(
        select(func.coalesce(func.sum(Contest.prize_amount), 0))
        .join(Winner, Winner.contest_id == Contest.id)
        .where(Winner.telegram_id == telegram_id)
    )
    last_r = await session.execute(
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


# ─── Admin global stats ───────────────────────────────────────────────────────

async def get_admin_status_stats(session: AsyncSession) -> dict:
    total_r  = await session.execute(select(func.count(User.id)))
    total    = total_r.scalar() or 0

    from sqlalchemy import case
    verified_r = await session.execute(
        select(func.count()).select_from(UserProfile).where(UserProfile.status == "verified")
    )
    pending_r = await session.execute(
        select(func.count()).select_from(UserProfile).where(UserProfile.status == "pending")
    )
    fake_r = await session.execute(
        select(func.count()).select_from(UserProfile).where(UserProfile.status == "fake")
    )
    blocked_r = await session.execute(
        select(func.count()).select_from(UserProfile).where(UserProfile.status == "banned")
    )
    afk_r = await session.execute(select(func.count()).where(User.is_afk == True))

    tasks_r     = await session.execute(select(func.count()).select_from(Task).where(Task.is_active == True))
    completed_r = await session.execute(select(func.count()).select_from(TaskLog).where(TaskLog.status == "completed"))
    penalties_r = await session.execute(select(func.coalesce(func.sum(UserBalance.penalties), 0)).select_from(UserBalance))
    earned_r    = await session.execute(select(func.coalesce(func.sum(UserBalance.balance), 0)).select_from(UserBalance))
    paidout_r   = await session.execute(select(func.coalesce(func.sum(UserBalance.paid_out), 0)).select_from(UserBalance))

    return {
        "total":      total,
        "verified":   verified_r.scalar() or 0,
        "pending":    pending_r.scalar() or 0,
        "fake":       fake_r.scalar() or 0,
        "banned_pro": blocked_r.scalar() or 0,
        "afk":        afk_r.scalar() or 0,
        "tasks":      tasks_r.scalar() or 0,
        "completed":  completed_r.scalar() or 0,
        "penalties":  float(penalties_r.scalar() or 0),
        "earned":     float(earned_r.scalar() or 0),
        "paid_out":   float(paidout_r.scalar() or 0),
    }


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
        if binance_id is not None: pd.binance_id = binance_id
        if stake_user is not None: pd.stake_user = stake_user
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

async def get_user_slot(session: AsyncSession, telegram_id: int) -> Optional[UserSlot]:
    result = await session.execute(select(UserSlot).where(UserSlot.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def update_user_slot(session: AsyncSession, telegram_id: int, slot_name: str, spins: int) -> UserSlot:
    result = await session.execute(select(UserSlot).where(UserSlot.telegram_id == telegram_id))
    us = result.scalar_one_or_none()
    today = date.today()
    if not us:
        us = UserSlot(telegram_id=telegram_id, slot_name=slot_name, spins=spins, slot_date=today)
        session.add(us)
    else:
        us.slot_name = slot_name; us.spins = spins; us.slot_date = today
    await session.commit()
    await session.refresh(us)
    return us


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
        gs.slot_name = slot_name; gs.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(gs)
    return gs


async def get_all_user_slot_ids(session: AsyncSession) -> list[int]:
    result = await session.execute(select(UserSlot.telegram_id))
    return list(result.scalars().all())


# ─── Bet posts ────────────────────────────────────────────────────────────────

async def create_bet_post(session: AsyncSession, text: str, admin_id: int,
                           media_id: Optional[str] = None, media_type: Optional[str] = None) -> BetPost:
    bp = BetPost(text=text, media_id=media_id, media_type=media_type, admin_id=admin_id)
    session.add(bp)
    await session.commit()
    await session.refresh(bp)
    return bp


async def list_bet_posts(session: AsyncSession, limit: int = 20) -> list[BetPost]:
    result = await session.execute(select(BetPost).order_by(BetPost.created_at.desc()).limit(limit))
    return list(result.scalars().all())


# ─── Contest system ───────────────────────────────────────────────────────────

async def get_active_contest(session: AsyncSession) -> Optional[Contest]:
    result = await session.execute(
        select(Contest).where(Contest.status == "active")
        .options(selectinload(Contest.participants))
        .order_by(Contest.created_at.desc())
    )
    return result.scalar_one_or_none()


async def create_contest(session: AsyncSession, title: str, prize_text: str,
                          prize_amount: float, winners_count: int) -> Contest:
    c = Contest(title=title, prize_text=prize_text, prize_amount=prize_amount, winners_count=winners_count)
    session.add(c)
    await session.commit()
    await session.refresh(c)
    return c


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


async def is_participant(session: AsyncSession, contest_id: int, telegram_id: int) -> bool:
    result = await session.execute(
        select(ContestParticipant).where(
            and_(ContestParticipant.contest_id == contest_id,
                 ContestParticipant.telegram_id == telegram_id)
        )
    )
    return result.scalar_one_or_none() is not None


async def add_participant(session: AsyncSession, contest_id: int, telegram_id: int) -> ContestParticipant:
    p = ContestParticipant(contest_id=contest_id, telegram_id=telegram_id)
    session.add(p)
    await session.commit()
    await session.refresh(p)
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
    return winners, total
