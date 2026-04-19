from datetime import datetime, date
from sqlalchemy import (
    BigInteger, Boolean, Column, Date, DateTime,
    Float, ForeignKey, Integer, String, Text, UniqueConstraint, func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ─── Profile status constants ─────────────────────────────────────────────────
# "new"      = ….. (default, no review yet)
# "pending"  = ⬜️ на рассмотрении
# "verified" = 🟩 верифицирован
# "fake"     = 🟥 фейк / мёртвый
# "banned"   = ⬛️ заблокирован
# "girl"     = 🟧 девушка + верифицирована
# "guy"      = 🟫 парень + верифицирован

STATUS_ICONS = {
    "new":      "…..",
    "pending":  "⬜️",
    "verified": "🟩",
    "fake":     "🟥",
    "banned":   "⬛️",
    "girl":     "🟧",
    "guy":      "🟫",
}

# Task access_level values
# "all"        - everything
# "new"        - only new/unverified
# "pending"    - only pending
# "verified"   - only verified (🟩 + 🟧 + 🟫)
# "no_fake"    - exclude fake
# "girl_ver"   - 🟧 girls + 🟩 verified
# "guy_ver"    - 🟫 guys + 🟩 verified
ACCESS_LEVELS = ["all", "new", "pending", "verified", "no_fake", "girl_ver", "guy_ver"]


class User(Base):
    __tablename__ = "users"
    id             = Column(Integer, primary_key=True)
    telegram_id    = Column(BigInteger, unique=True, nullable=False, index=True)
    username       = Column(String(255), nullable=True)
    user_number    = Column(Integer, unique=True, nullable=True)
    lang           = Column(String(5), default="", nullable=False)
    is_banned      = Column(Boolean, default=False, nullable=False)
    loot_banned    = Column(Boolean, default=False, nullable=False)
    is_afk         = Column(Boolean, default=False, nullable=False)
    afk_since      = Column(DateTime, nullable=True)
    last_review_at         = Column(DateTime, nullable=True)
    last_loot_at           = Column(DateTime, nullable=True)
    last_stake_change_at   = Column(DateTime, nullable=True)
    last_binance_change_at = Column(DateTime, nullable=True)
    last_report_at         = Column(DateTime, nullable=True)
    last_withdrawal_at     = Column(DateTime, nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    payment   = relationship("PaymentData", back_populates="user", uselist=False)
    profile   = relationship("UserProfile", back_populates="user", uselist=False)
    balance   = relationship("UserBalance", back_populates="user", uselist=False)
    slot      = relationship("UserSlot", back_populates="user", uselist=False)
    task_logs = relationship("TaskLog", back_populates="user")


class UserProfile(Base):
    __tablename__ = "user_profiles"
    id          = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, ForeignKey("users.telegram_id"), unique=True, nullable=False)
    instagram   = Column(String(255), nullable=True)
    threads     = Column(String(255), nullable=True)
    facebook    = Column(String(512), nullable=True)
    twitter     = Column(String(255), nullable=True)
    # status: new | pending | verified | fake | banned | girl | guy
    status      = Column(String(20), default="new", nullable=False)
    bonus_paid  = Column(Boolean, default=False, nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship("User", back_populates="profile")


class UserBalance(Base):
    __tablename__ = "user_balances"
    id          = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, ForeignKey("users.telegram_id"), unique=True, nullable=False)
    balance     = Column(Float, default=0.0, nullable=False)
    paid_out    = Column(Float, default=0.0, nullable=False)
    penalties   = Column(Float, default=0.0, nullable=False)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship("User", back_populates="balance")


class WithdrawalRequest(Base):
    __tablename__ = "withdrawal_requests"
    id           = Column(Integer, primary_key=True)
    telegram_id  = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    amount       = Column(Float, nullable=False)
    status       = Column(String(20), default="pending", nullable=False)
    moder_msg_id = Column(Integer, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)
    resolved_at  = Column(DateTime, nullable=True)


class Task(Base):
    __tablename__ = "tasks"
    id           = Column(Integer, primary_key=True)
    platform     = Column(String(50), nullable=False)
    link         = Column(String(1024), nullable=False)
    max_users    = Column(Integer, nullable=False, default=15)
    action_type  = Column(String(100), nullable=False)
    description  = Column(Text, nullable=True)
    reward       = Column(Float, nullable=False, default=0.20)
    # access_level: all | new | pending | verified | no_fake | girl_ver | guy_ver
    access_level = Column(String(30), default="all", nullable=False)
    is_active    = Column(Boolean, default=True, nullable=False)
    admin_id     = Column(BigInteger, nullable=False)
    created_at   = Column(DateTime, default=datetime.utcnow)
    comments = relationship("TaskComment", back_populates="task")
    logs     = relationship("TaskLog", back_populates="task")


class TaskComment(Base):
    __tablename__ = "task_comments"
    id       = Column(Integer, primary_key=True)
    task_id  = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    text     = Column(Text, nullable=False)
    is_used  = Column(Boolean, default=False, nullable=False)
    used_by  = Column(BigInteger, nullable=True)
    task = relationship("Task", back_populates="comments")


class TaskLog(Base):
    __tablename__ = "task_logs"
    id           = Column(Integer, primary_key=True)
    task_id      = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    telegram_id  = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    comment_id   = Column(Integer, ForeignKey("task_comments.id"), nullable=True)
    status       = Column(String(30), default="accepted", nullable=False)
    accepted_at  = Column(DateTime, default=datetime.utcnow)
    expires_at   = Column(DateTime, nullable=True)
    moder_msg_id = Column(Integer, nullable=True)
    task = relationship("Task", back_populates="logs")
    user = relationship("User", back_populates="task_logs")


class PaymentData(Base):
    """
    Stake ID and Binance ID are GLOBALLY UNIQUE across all users.
    DB enforces uniqueness via UniqueConstraint.
    """
    __tablename__ = "payment_data"
    __table_args__ = (
        UniqueConstraint("stake_user", name="uq_payment_stake_user"),
        UniqueConstraint("binance_id", name="uq_payment_binance_id"),
    )
    id          = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, ForeignKey("users.telegram_id"), unique=True, nullable=False)
    binance_id  = Column(String(256), nullable=True)
    stake_user  = Column(String(256), nullable=True)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship("User", back_populates="payment")


class UserSlot(Base):
    __tablename__ = "user_slots"
    id          = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, ForeignKey("users.telegram_id"), unique=True, nullable=False)
    slot_name   = Column(String(256), nullable=False, default="")
    spins       = Column(Integer, nullable=False, default=69)
    slot_date   = Column(Date, nullable=False, default=date.today)
    user = relationship("User", back_populates="slot")


class GlobalSlot(Base):
    __tablename__ = "global_slot"
    id         = Column(Integer, primary_key=True)
    slot_name  = Column(String(256), nullable=False, default="")
    updated_at = Column(DateTime, default=datetime.utcnow)


class BetPost(Base):
    __tablename__ = "bet_posts"
    id         = Column(Integer, primary_key=True)
    text       = Column(Text, nullable=False)
    media_id   = Column(String(512), nullable=True)
    media_type = Column(String(20), nullable=True)
    admin_id   = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())


class Contest(Base):
    __tablename__ = "contests"
    id            = Column(Integer, primary_key=True)
    title         = Column(String(1024), nullable=False)
    prize_text    = Column(String(512), nullable=False)
    prize_amount  = Column(Float, nullable=True, default=0)
    winners_count = Column(Integer, nullable=False, default=1)
    status        = Column(String(20), default="active", nullable=False)
    created_at    = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    finished_at   = Column(DateTime, nullable=True)
    participants = relationship("ContestParticipant", back_populates="contest")
    winners      = relationship("Winner", back_populates="contest")


class ContestParticipant(Base):
    __tablename__ = "contest_participants"
    id          = Column(Integer, primary_key=True)
    contest_id  = Column(Integer, ForeignKey("contests.id"), nullable=False)
    telegram_id = Column(BigInteger, nullable=False, index=True)
    created_at  = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    contest = relationship("Contest", back_populates="participants")
    user    = relationship("User", foreign_keys=[telegram_id],
                           primaryjoin="ContestParticipant.telegram_id == User.telegram_id")


class Winner(Base):
    __tablename__ = "winners"
    id          = Column(Integer, primary_key=True)
    contest_id  = Column(Integer, ForeignKey("contests.id"), nullable=False)
    telegram_id = Column(BigInteger, nullable=False, index=True)
    created_at  = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    contest = relationship("Contest", back_populates="winners")
    user    = relationship("User", foreign_keys=[telegram_id],
                           primaryjoin="Winner.telegram_id == User.telegram_id")
