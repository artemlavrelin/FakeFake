from datetime import datetime
from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime,
    ForeignKey, Integer, String, func
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    is_banned = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    participations = relationship("ContestParticipant", back_populates="user", foreign_keys="ContestParticipant.telegram_id", primaryjoin="User.telegram_id == ContestParticipant.telegram_id")
    wins = relationship("Winner", back_populates="user", foreign_keys="Winner.telegram_id", primaryjoin="User.telegram_id == Winner.telegram_id")


class Contest(Base):
    __tablename__ = "contests"

    id = Column(Integer, primary_key=True)
    title = Column(String(512), nullable=False)
    prize_text = Column(String(2048), nullable=False)
    winners_count = Column(Integer, nullable=False, default=1)
    status = Column(String(20), default="active", nullable=False)  # active / finished
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    finished_at = Column(DateTime, nullable=True)

    participants = relationship("ContestParticipant", back_populates="contest")
    winners = relationship("Winner", back_populates="contest")


class ContestParticipant(Base):
    __tablename__ = "contest_participants"

    id = Column(Integer, primary_key=True)
    contest_id = Column(Integer, ForeignKey("contests.id"), nullable=False)
    telegram_id = Column(BigInteger, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    contest = relationship("Contest", back_populates="participants")
    user = relationship("User", foreign_keys=[telegram_id], primaryjoin="ContestParticipant.telegram_id == User.telegram_id")


class Winner(Base):
    __tablename__ = "winners"

    id = Column(Integer, primary_key=True)
    contest_id = Column(Integer, ForeignKey("contests.id"), nullable=False)
    telegram_id = Column(BigInteger, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    contest = relationship("Contest", back_populates="winners")
    user = relationship("User", foreign_keys=[telegram_id], primaryjoin="Winner.telegram_id == User.telegram_id")
