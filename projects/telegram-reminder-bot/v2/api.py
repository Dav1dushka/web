import os

from fastapi import FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from .models import Base, Reminder

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://reminders:reminders@localhost:5432/reminders",
)

engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
Session = async_sessionmaker(engine, expire_on_commit=False)
app = FastAPI(title="Reminder Bot Admin API")


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/reminders")
async def reminders():
    async with Session() as session:
        rows = (
            await session.execute(
                select(Reminder)
                .order_by(Reminder.reminder_at.desc())
                .limit(200)
            )
        ).scalars().all()

    return [
        {
            "id": r.id,
            "owner_id": r.owner_id,
            "title": r.title,
            "category": r.category,
            "priority": r.priority,
            "reminder_at": r.reminder_at.isoformat(),
            "repeat": r.repeat,
            "status": r.status,
        }
        for r in rows
    ]


@app.post("/api/reminders/{reminder_id}/archive")
async def archive(reminder_id: int):
    async with Session() as session:
        reminder = await session.get(Reminder, reminder_id)
        if not reminder:
            raise HTTPException(status_code=404, detail="Reminder not found")
        reminder.status = "archived"
        await session.commit()

    return {"ok": True}
