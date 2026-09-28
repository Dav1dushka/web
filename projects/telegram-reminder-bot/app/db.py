from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .config import get_settings

settings = get_settings()
engine = create_async_engine(settings.database_url, pool_pre_ping=True)
Session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    language: Mapped[str] = mapped_column(String(4), default="")
    timezone: Mapped[str] = mapped_column(String(64), default=settings.default_timezone)
    digest_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    digest_hour: Mapped[int] = mapped_column(Integer, default=9)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, index=True)
    title: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(32), default="other")
    priority: Mapped[str] = mapped_column(String(16), default="medium")
    reminder_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    repeat: Mapped[str] = mapped_column(String(32), default="once")
    lead_minutes: Mapped[str] = mapped_column(String(64), default="0")
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)
    share_token: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class SharedMember(Base):
    __tablename__ = "shared_members"

    reminder_id: Mapped[int] = mapped_column(
        ForeignKey("reminders.id", ondelete="CASCADE"),
        primary_key=True,
    )
    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    role: Mapped[str] = mapped_column(String(16), default="viewer")
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class Delivery(Base):
    __tablename__ = "deliveries"

    reminder_id: Mapped[int] = mapped_column(ForeignKey("reminders.id", ondelete="CASCADE"), primary_key=True)
    occurrence_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    lead_minutes: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipient_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def ensure_user(
    session: AsyncSession,
    telegram_id: int,
    language: str = "",
) -> User:
    user = await session.get(User, telegram_id)

    if user:
        return user

    user = User(telegram_id=telegram_id, language=language)
    session.add(user)
    await session.commit()
    return user


async def stats(session: AsyncSession, telegram_id: int) -> dict[str, int]:
    result: dict[str, int] = {}

    for key, status in (
        ("active", "active"),
        ("completed", "completed"),
        ("archived", "archived"),
    ):
        count = await session.scalar(
            select(func.count())
            .select_from(Reminder)
            .where(
                Reminder.owner_id == telegram_id,
                Reminder.status == status,
            )
        )
        result[key] = int(count or 0)

    return result
