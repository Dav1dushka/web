from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, index=True)
    title: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(32), default="other")
    priority: Mapped[str] = mapped_column(String(16), default="medium")
    reminder_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    repeat: Mapped[str] = mapped_column(String(32), default="once")
    status: Mapped[str] = mapped_column(String(16), default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
