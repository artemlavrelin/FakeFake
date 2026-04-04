from datetime import datetime
from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime,
    Float, ForeignKey, Integer, String, func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True)
    telegram_id   = Column(BigInteger, unique=True, nullable=False, index=True)
    username      = Column(String(255), nullable=True)
    user_number   = Column(Integer, unique=True, nullable=True)   # ▫️1–9999
    is_banned     = Column(Boolean, default=False, nullable=False)
    created_at    = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    payment       = relationship("PaymentData", back_populates="user", uselist=False)


class Contest(Base):
    __tablename__ = "contests"

    id            = Column(Integer, primary_key=True)
    title         = Column(String(1024), nullable=False)
    prize_text    = Column(String(512), nullable=False)
    prize_amount  = Column(Float, nullable=True, default=0)
    winners_count = Column(Integer, nullable=False, default=1)
    status        = Column(String(20), default="active", nullable=False)  # active|finished|cancelled
    created_at    = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    finished_at   = Column(DateTime, nullable=True)

    participants  = relationship("ContestParticipant", back_populates="contest")
    winners       = relationship("Winner", back_populates="contest")
    bonus_winners = relationship("BonusWinner", back_populates="contest")


class ContestParticipant(Base):
    __tablename__ = "contest_participants"

    id          = Column(Integer, primary_key=True)
    contest_id  = Column(Integer, ForeignKey("contests.id"), nullable=False)
    telegram_id = Column(BigInteger, nullable=False, index=True)
    created_at  = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    contest     = relationship("Contest", back_populates="participants")
    user        = relationship(
        "User", foreign_keys=[telegram_id],
        primaryjoin="ContestParticipant.telegram_id == User.telegram_id",
    )


class Winner(Base):
    __tablename__ = "winners"

    id          = Column(Integer, primary_key=True)
    contest_id  = Column(Integer, ForeignKey("contests.id"), nullable=False)
    telegram_id = Column(BigInteger, nullable=False, index=True)
    created_at  = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    contest     = relationship("Contest", back_populates="winners")
    user        = relationship(
        "User", foreign_keys=[telegram_id],
        primaryjoin="Winner.telegram_id == User.telegram_id",
    )


class BonusWinner(Base):
    """Records from /bonus_draw — stored separately from main draw."""
    __tablename__ = "bonus_winners"

    id          = Column(Integer, primary_key=True)
    contest_id  = Column(Integer, ForeignKey("contests.id"), nullable=False)
    telegram_id = Column(BigInteger, nullable=False, index=True)
    note        = Column(String(512), nullable=True)   # admin free-text label
    created_at  = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    contest     = relationship("Contest", back_populates="bonus_winners")
    user        = relationship(
        "User", foreign_keys=[telegram_id],
        primaryjoin="BonusWinner.telegram_id == User.telegram_id",
    )


class PaymentData(Base):
    """Stores Binance ID / Stake ID per user. Edit only via admin commands."""
    __tablename__ = "payment_data"

    id          = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, ForeignKey("users.telegram_id"), unique=True, nullable=False)
    binance_id  = Column(String(256), nullable=True)
    stake_id    = Column(String(256), nullable=True)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user        = relationship("User", back_populates="payment")
