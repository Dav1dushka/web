import asyncio
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import aiosqlite
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

DB_NAME = "reminders.db"
CHECK_EVERY_SECONDS = 30
TIMEZONE = ZoneInfo(os.getenv("BOT_TIMEZONE", "Europe/Prague"))

dp = Dispatcher()


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                reminder_at TEXT NOT NULL,
                repeat TEXT NOT NULL DEFAULT 'none',
                sent_at TEXT
            )
            """
        )
        await db.commit()


def parse_reminder(text: str):
    parts = [part.strip() for part in text.split("|")]

    if len(parts) < 2 or len(parts) > 3:
        raise ValueError("Use: YYYY-MM-DD HH:MM | title | repeat")

    date_text, title = parts[0], parts[1]
    repeat = parts[2].lower() if len(parts) == 3 else "none"

    if repeat not in {"none", "yearly"}:
        raise ValueError("Repeat must be: none or yearly")

    try:
        reminder_at = datetime.strptime(
            date_text,
            "%Y-%m-%d %H:%M",
        ).replace(tzinfo=TIMEZONE)
    except ValueError:
        raise ValueError("Date format should be YYYY-MM-DD HH:MM")

    return reminder_at, title, repeat


@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "Hi! I'm a simple reminder bot.\n\n"
        "/add YYYY-MM-DD HH:MM | title | repeat\n"
        "/list\n"
        "/today\n"
        "/delete ID\n"
        "/help"
    )


@dp.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        "Example:\n"
        "/add 2026-10-27 09:00 | Mom's birthday | yearly\n\n"
        "repeat can be: none or yearly"
    )


@dp.message(Command("add"))
async def add_reminder(message: Message):
    payload = message.text.removeprefix("/add").strip()

    try:
        reminder_at, title, repeat = parse_reminder(payload)
    except ValueError as exc:
        await message.answer(str(exc))
        return

    if reminder_at <= datetime.now(TIMEZONE):
        await message.answer("That time is already in the past.")
        return

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            INSERT INTO reminders (
                telegram_id,
                title,
                reminder_at,
                repeat
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                message.from_user.id,
                title,
                reminder_at.isoformat(),
                repeat,
            ),
        )
        await db.commit()

    repeat_text = "every year" if repeat == "yearly" else "once"

    await message.answer(
        f"Added ✅\n\n"
        f"{title}\n"
        f"{reminder_at:%Y-%m-%d %H:%M %Z}\n"
        f"Repeat: {repeat_text}"
    )


@dp.message(Command("list"))
async def list_reminders(message: Message):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """
            SELECT id, title, reminder_at, repeat
            FROM reminders
            WHERE telegram_id = ? AND sent_at IS NULL
            ORDER BY reminder_at
            """,
            (message.from_user.id,),
        )
        rows = await cursor.fetchall()

    if not rows:
        await message.answer("No active reminders.")
        return

    lines = ["📅 Your reminders:"]
    for reminder_id, title, reminder_at, repeat in rows:
        reminder_dt = datetime.fromisoformat(reminder_at).astimezone(TIMEZONE)
        repeat_text = "yearly" if repeat == "yearly" else "once"
        lines.append(
            f"#{reminder_id} — {title} — "
            f"{reminder_dt:%Y-%m-%d %H:%M} — {repeat_text}"
        )

    await message.answer("\n".join(lines))


@dp.message(Command("today"))
async def today(message: Message):
    today_value = datetime.now(TIMEZONE).date().isoformat()

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """
            SELECT id, title, reminder_at
            FROM reminders
            WHERE telegram_id = ?
              AND sent_at IS NULL
              AND reminder_at LIKE ?
            ORDER BY reminder_at
            """,
            (message.from_user.id, f"{today_value}%"),
        )
        rows = await cursor.fetchall()

    if not rows:
        await message.answer("Nothing planned for today.")
        return

    lines = ["Today:"]
    for reminder_id, title, reminder_at in rows:
        reminder_dt = datetime.fromisoformat(reminder_at).astimezone(TIMEZONE)
        lines.append(
            f"#{reminder_id} — {reminder_dt:%H:%M} — {title}"
        )

    await message.answer("\n".join(lines))


@dp.message(Command("delete"))
async def delete_reminder(message: Message):
    payload = message.text.removeprefix("/delete").strip()

    try:
        reminder_id = int(payload)
    except ValueError:
        await message.answer("Use: /delete ID")
        return

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """
            DELETE FROM reminders
            WHERE id = ? AND telegram_id = ?
            """,
            (reminder_id, message.from_user.id),
        )
        await db.commit()

    if cursor.rowcount == 0:
        await message.answer("Reminder not found.")
        return

    await message.answer("Deleted.")


async def deliver_reminders(bot: Bot):
    while True:
        now = datetime.now(TIMEZONE).replace(second=0, microsecond=0)

        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute(
                """
                SELECT id, telegram_id, title, reminder_at, repeat
                FROM reminders
                WHERE sent_at IS NULL
                  AND reminder_at <= ?
                ORDER BY reminder_at
                """,
                (now.isoformat(),),
            )
            rows = await cursor.fetchall()

            for reminder_id, telegram_id, title, reminder_at, repeat in rows:
                await bot.send_message(
                    telegram_id,
                    f"🔔 Reminder\n\n{title}",
                )

                if repeat == "yearly":
                    old_date = datetime.fromisoformat(reminder_at)
                    next_date = old_date.replace(year=old_date.year + 1)

                    await db.execute(
                        """
                        UPDATE reminders
                        SET reminder_at = ?
                        WHERE id = ?
                        """,
                        (next_date.isoformat(), reminder_id),
                    )
                else:
                    await db.execute(
                        """
                        UPDATE reminders
                        SET sent_at = ?
                        WHERE id = ?
                        """,
                        (datetime.now(timezone.utc).isoformat(), reminder_id),
                    )

            await db.commit()

        await asyncio.sleep(CHECK_EVERY_SECONDS)


async def main():
    token = os.getenv("BOT_TOKEN")

    if not token:
        raise RuntimeError("BOT_TOKEN is not set")

    await init_db()

    async with Bot(token=token) as bot:
        await bot.delete_webhook(drop_pending_updates=False)
        me = await bot.get_me()
        print(f"Bot started: @{me.username}", flush=True)

        await asyncio.gather(
            dp.start_polling(bot),
            deliver_reminders(bot),
        )


if __name__ == "__main__":
    asyncio.run(main())
