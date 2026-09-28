import asyncio
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

DB_NAME = "reminders.db"
CHECK_EVERY_SECONDS = 30
TIMEZONE = ZoneInfo(os.getenv("BOT_TIMEZONE", "Europe/Prague"))

dp = Dispatcher()

LANGUAGES = {
    "ru": {"name": "Русский", "flag": "🇷🇺"},
    "en": {"name": "English", "flag": "🇬🇧"},
    "it": {"name": "Italiano", "flag": "🇮🇹"},
    "uk": {"name": "Українська", "flag": "🇺🇦"},
}

TEXT = {
    "ru": {
        "choose_language": "Выберите язык:",
        "welcome": "Привет! Я помогу не забыть важные дела и даты. 🔔",
        "menu": "Что хочешь сделать?",
        "add": "➕ Добавить",
        "list": "📅 Мои напоминания",
        "today": "📌 Сегодня",
        "language": "🌐 Язык",
        "help": "ℹ️ Помощь",
        "add_help": "Формат:\n/add 2026-10-27 09:00 | День рождения мамы | yearly",
        "repeat_yearly": "каждый год",
        "repeat_once": "один раз",
        "added": "Добавлено ✅",
        "no_reminders": "У тебя нет активных напоминаний.",
        "reminders": "📅 Твои напоминания:",
        "nothing_today": "На сегодня ничего нет.",
        "deleted": "Удалено.",
        "not_found": "Напоминание не найдено.",
        "bad_date": "Формат даты: YYYY-MM-DD HH:MM",
        "bad_repeat": "Повтор может быть: none или yearly",
        "past": "Это время уже прошло.",
        "use_delete": "Используй: /delete ID",
        "reminder": "🔔 Напоминание",
        "language_saved": "Язык сохранён.",
    },
    "en": {
        "choose_language": "Choose your language:",
        "welcome": "Hi! I'll help you remember important dates and tasks. 🔔",
        "menu": "What do you want to do?",
        "add": "➕ Add reminder",
        "list": "📅 My reminders",
        "today": "📌 Today",
        "language": "🌐 Language",
        "help": "ℹ️ Help",
        "add_help": "Format:\n/add 2026-10-27 09:00 | Mom's birthday | yearly",
        "repeat_yearly": "every year",
        "repeat_once": "once",
        "added": "Added ✅",
        "no_reminders": "You have no active reminders.",
        "reminders": "📅 Your reminders:",
        "nothing_today": "Nothing planned for today.",
        "deleted": "Deleted.",
        "not_found": "Reminder not found.",
        "bad_date": "Date format: YYYY-MM-DD HH:MM",
        "bad_repeat": "Repeat can be: none or yearly",
        "past": "That time is already in the past.",
        "use_delete": "Use: /delete ID",
        "reminder": "🔔 Reminder",
        "language_saved": "Language saved.",
    },
    "it": {
        "choose_language": "Scegli la lingua:",
        "welcome": "Ciao! Ti aiuterò a non dimenticare date e attività importanti. 🔔",
        "menu": "Cosa vuoi fare?",
        "add": "➕ Aggiungi",
        "list": "📅 I miei promemoria",
        "today": "📌 Oggi",
        "language": "🌐 Lingua",
        "help": "ℹ️ Aiuto",
        "add_help": "Formato:\n/add 2026-10-27 09:00 | Compleanno mamma | yearly",
        "repeat_yearly": "ogni anno",
        "repeat_once": "una volta",
        "added": "Aggiunto ✅",
        "no_reminders": "Non hai promemoria attivi.",
        "reminders": "📅 I tuoi promemoria:",
        "nothing_today": "Niente in programma per oggi.",
        "deleted": "Eliminato.",
        "not_found": "Promemoria non trovato.",
        "bad_date": "Formato data: YYYY-MM-DD HH:MM",
        "bad_repeat": "La ripetizione può essere: none o yearly",
        "past": "Questo orario è già passato.",
        "use_delete": "Usa: /delete ID",
        "reminder": "🔔 Promemoria",
        "language_saved": "Lingua salvata.",
    },
    "uk": {
        "choose_language": "Оберіть мову:",
        "welcome": "Привіт! Я допоможу не забувати важливі дати та справи. 🔔",
        "menu": "Що хочеш зробити?",
        "add": "➕ Додати",
        "list": "📅 Мої нагадування",
        "today": "📌 Сьогодні",
        "language": "🌐 Мова",
        "help": "ℹ️ Допомога",
        "add_help": "Формат:\n/add 2026-10-27 09:00 | День народження мами | yearly",
        "repeat_yearly": "щороку",
        "repeat_once": "один раз",
        "added": "Додано ✅",
        "no_reminders": "У тебе немає активних нагадувань.",
        "reminders": "📅 Твої нагадування:",
        "nothing_today": "На сьогодні нічого немає.",
        "deleted": "Видалено.",
        "not_found": "Нагадування не знайдено.",
        "bad_date": "Формат дати: YYYY-MM-DD HH:MM",
        "bad_repeat": "Повтор може бути: none або yearly",
        "past": "Цей час уже минув.",
        "use_delete": "Використовуй: /delete ID",
        "reminder": "🔔 Нагадування",
        "language_saved": "Мову збережено.",
    },
}


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

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                language TEXT NOT NULL DEFAULT 'en'
            )
            """
        )

        await db.commit()


async def get_language(telegram_id: int) -> str | None:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT language FROM users WHERE telegram_id = ?",
            (telegram_id,),
        )
        row = await cursor.fetchone()

    return row[0] if row else None


async def set_language(telegram_id: int, language: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            INSERT INTO users (telegram_id, language)
            VALUES (?, ?)
            ON CONFLICT(telegram_id)
            DO UPDATE SET language = excluded.language
            """,
            (telegram_id, language),
        )
        await db.commit()


def language_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{LANGUAGES['ru']['flag']} {LANGUAGES['ru']['name']}",
                    callback_data="lang:ru",
                ),
                InlineKeyboardButton(
                    text=f"{LANGUAGES['en']['flag']} {LANGUAGES['en']['name']}",
                    callback_data="lang:en",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"{LANGUAGES['it']['flag']} {LANGUAGES['it']['name']}",
                    callback_data="lang:it",
                ),
                InlineKeyboardButton(
                    text=f"{LANGUAGES['uk']['flag']} {LANGUAGES['uk']['name']}",
                    callback_data="lang:uk",
                ),
            ],
        ]
    )


def main_keyboard(language: str):
    t = TEXT[language]

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=t["add"]),
                KeyboardButton(text=t["list"]),
            ],
            [
                KeyboardButton(text=t["today"]),
                KeyboardButton(text=t["language"]),
            ],
            [
                KeyboardButton(text=t["help"]),
            ],
        ],
        resize_keyboard=True,
    )


async def send_main_menu(message: Message, language: str):
    t = TEXT[language]
    await message.answer(
        f"{t['welcome']}\n\n{t['menu']}",
        reply_markup=main_keyboard(language),
    )


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
    language = await get_language(message.from_user.id)

    if language is None:
        await message.answer(
            "Choose your language / Выберите язык / Scegli la lingua / Оберіть мову:",
            reply_markup=language_keyboard(),
        )
        return

    await send_main_menu(message, language)


@dp.callback_query(F.data.startswith("lang:"))
async def language_selected(callback: CallbackQuery):
    language = callback.data.split(":", 1)[1]

    if language not in LANGUAGES:
        await callback.answer()
        return

    await set_language(callback.from_user.id, language)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(TEXT[language]["language_saved"])
    await send_main_menu(callback.message, language)
    await callback.answer()


@dp.message(Command("help"))
async def help_command(message: Message):
    language = await get_language(message.from_user.id) or "en"
    await message.answer(
        TEXT[language]["add_help"],
        reply_markup=main_keyboard(language),
    )


@dp.message(Command("add"))
async def add_reminder(message: Message):
    language = await get_language(message.from_user.id) or "en"
    t = TEXT[language]
    payload = message.text.removeprefix("/add").strip()

    try:
        reminder_at, title, repeat = parse_reminder(payload)
    except ValueError:
        await message.answer(t["add_help"])
        return

    if reminder_at <= datetime.now(TIMEZONE):
        await message.answer(t["past"])
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

    repeat_text = t["repeat_yearly"] if repeat == "yearly" else t["repeat_once"]

    await message.answer(
        f"{t['added']}\n\n"
        f"{title}\n"
        f"{reminder_at:%Y-%m-%d %H:%M %Z}\n"
        f"{repeat_text}",
        reply_markup=main_keyboard(language),
    )


@dp.message(Command("list"))
async def list_reminders(message: Message):
    language = await get_language(message.from_user.id) or "en"
    t = TEXT[language]

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
        await message.answer(
            t["no_reminders"],
            reply_markup=main_keyboard(language),
        )
        return

    lines = [t["reminders"]]
    for reminder_id, title, reminder_at, repeat in rows:
        reminder_dt = datetime.fromisoformat(reminder_at).astimezone(TIMEZONE)
        repeat_text = t["repeat_yearly"] if repeat == "yearly" else t["repeat_once"]
        lines.append(
            f"#{reminder_id} — {title} — "
            f"{reminder_dt:%Y-%m-%d %H:%M} — {repeat_text}"
        )

    await message.answer(
        "\n".join(lines),
        reply_markup=main_keyboard(language),
    )


@dp.message(Command("today"))
async def today(message: Message):
    language = await get_language(message.from_user.id) or "en"
    t = TEXT[language]
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
        await message.answer(
            t["nothing_today"],
            reply_markup=main_keyboard(language),
        )
        return

    lines = [t["today"]]
    for reminder_id, title, reminder_at in rows:
        reminder_dt = datetime.fromisoformat(reminder_at).astimezone(TIMEZONE)
        lines.append(f"#{reminder_id} — {reminder_dt:%H:%M} — {title}")

    await message.answer(
        "\n".join(lines),
        reply_markup=main_keyboard(language),
    )


@dp.message(Command("delete"))
async def delete_reminder(message: Message):
    language = await get_language(message.from_user.id) or "en"
    t = TEXT[language]
    payload = message.text.removeprefix("/delete").strip()

    try:
        reminder_id = int(payload)
    except ValueError:
        await message.answer(t["use_delete"])
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
        await message.answer(t["not_found"])
        return

    await message.answer(
        t["deleted"],
        reply_markup=main_keyboard(language),
    )


@dp.message(F.text)
async def menu_buttons(message: Message):
    language = await get_language(message.from_user.id)
    if not language:
        await message.answer(
            TEXT["en"]["choose_language"],
            reply_markup=language_keyboard(),
        )
        return

    t = TEXT[language]

    if message.text == t["add"]:
        await message.answer(
            t["add_help"],
            reply_markup=main_keyboard(language),
        )
        return

    if message.text == t["list"]:
        await list_reminders(message)
        return

    if message.text == t["today"]:
        await today(message)
        return

    if message.text == t["language"]:
        await message.answer(
            t["choose_language"],
            reply_markup=language_keyboard(),
        )
        return

    if message.text == t["help"]:
        await help_command(message)


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
                language = await get_language(telegram_id) or "en"
                await bot.send_message(
                    telegram_id,
                    f"{TEXT[language]['reminder']}\n\n{title}",
                    reply_markup=main_keyboard(language),
                )

                if repeat == "yearly":
                    old_date = datetime.fromisoformat(reminder_at)
                    try:
                        next_date = old_date.replace(year=old_date.year + 1)
                    except ValueError:
                        next_date = old_date.replace(
                            year=old_date.year + 1,
                            day=28,
                        )

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
                        (
                            datetime.now(timezone.utc).isoformat(),
                            reminder_id,
                        ),
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
