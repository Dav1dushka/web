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
    Message,
)

DB_NAME = "reminders.db"
CHECK_EVERY_SECONDS = 30
TIMEZONE = ZoneInfo(os.getenv("BOT_TIMEZONE", "Europe/Prague"))

dp = Dispatcher()

LANGUAGES = {
    "ru": ("🇷🇺", "Русский"),
    "en": ("🇬🇧", "English"),
    "it": ("🇮🇹", "Italiano"),
    "uk": ("🇺🇦", "Українська"),
}

TEXT = {
    "ru": {
        "choose_language": "Выбери язык бота:",
        "welcome": "⏰ Привет!\nЯ помогу не забыть важные даты и дела.",
        "menu": "Главное меню",
        "add": "➕ Добавить напоминание",
        "list": "📅 Мои напоминания",
        "today": "📌 Сегодня",
        "language": "🌐 Язык",
        "help": "ℹ️ Помощь",
        "add_help": (
            "➕ <b>Новое напоминание</b>\n\n"
            "Пока можно добавить его так:\n"
            "<code>/add 2026-10-27 09:00 | День рождения мамы | yearly</code>\n\n"
            "Третий параметр <code>yearly</code> делает напоминание ежегодным."
        ),
        "repeat_yearly": "каждый год",
        "repeat_once": "один раз",
        "added": "✅ Напоминание добавлено",
        "no_reminders": "📭 Пока нет активных напоминаний.",
        "reminders": "📅 Твои напоминания:",
        "nothing_today": "📭 На сегодня ничего нет.",
        "deleted": "🗑 Удалено.",
        "not_found": "Не нашёл такое напоминание.",
        "past": "Это время уже прошло.",
        "use_delete": "Используй: /delete ID",
        "reminder": "🔔 Напоминание",
        "language_saved": "✅ Язык сохранён.",
        "back": "↩️ Назад",
        "delete_hint": "Чтобы удалить: /delete ID",
    },
    "en": {
        "choose_language": "Choose your bot language:",
        "welcome": "⏰ Hi!\nI'll help you remember important dates and tasks.",
        "menu": "Main menu",
        "add": "➕ Add reminder",
        "list": "📅 My reminders",
        "today": "📌 Today",
        "language": "🌐 Language",
        "help": "ℹ️ Help",
        "add_help": (
            "➕ <b>New reminder</b>\n\n"
            "For now you can add one like this:\n"
            "<code>/add 2026-10-27 09:00 | Mom's birthday | yearly</code>\n\n"
            "Use <code>yearly</code> for a reminder that repeats every year."
        ),
        "repeat_yearly": "every year",
        "repeat_once": "once",
        "added": "✅ Reminder added",
        "no_reminders": "📭 You have no active reminders.",
        "reminders": "📅 Your reminders:",
        "nothing_today": "📭 Nothing planned for today.",
        "deleted": "🗑 Deleted.",
        "not_found": "I couldn't find that reminder.",
        "past": "That time is already in the past.",
        "use_delete": "Use: /delete ID",
        "reminder": "🔔 Reminder",
        "language_saved": "✅ Language saved.",
        "back": "↩️ Back",
        "delete_hint": "To delete one: /delete ID",
    },
    "it": {
        "choose_language": "Scegli la lingua del bot:",
        "welcome": "⏰ Ciao!\nTi aiuterò a ricordare date e attività importanti.",
        "menu": "Menu principale",
        "add": "➕ Aggiungi promemoria",
        "list": "📅 I miei promemoria",
        "today": "📌 Oggi",
        "language": "🌐 Lingua",
        "help": "ℹ️ Aiuto",
        "add_help": (
            "➕ <b>Nuovo promemoria</b>\n\n"
            "Per ora puoi aggiungerlo così:\n"
            "<code>/add 2026-10-27 09:00 | Compleanno mamma | yearly</code>\n\n"
            "Usa <code>yearly</code> per ripeterlo ogni anno."
        ),
        "repeat_yearly": "ogni anno",
        "repeat_once": "una volta",
        "added": "✅ Promemoria aggiunto",
        "no_reminders": "📭 Non hai promemoria attivi.",
        "reminders": "📅 I tuoi promemoria:",
        "nothing_today": "📭 Niente in programma per oggi.",
        "deleted": "🗑 Eliminato.",
        "not_found": "Non ho trovato quel promemoria.",
        "past": "Questo orario è già passato.",
        "use_delete": "Usa: /delete ID",
        "reminder": "🔔 Promemoria",
        "language_saved": "✅ Lingua salvata.",
        "back": "↩️ Indietro",
        "delete_hint": "Per eliminarne uno: /delete ID",
    },
    "uk": {
        "choose_language": "Оберіть мову бота:",
        "welcome": "⏰ Привіт!\nЯ допоможу не забувати важливі дати та справи.",
        "menu": "Головне меню",
        "add": "➕ Додати нагадування",
        "list": "📅 Мої нагадування",
        "today": "📌 Сьогодні",
        "language": "🌐 Мова",
        "help": "ℹ️ Допомога",
        "add_help": (
            "➕ <b>Нове нагадування</b>\n\n"
            "Поки що можна додати так:\n"
            "<code>/add 2026-10-27 09:00 | День народження мами | yearly</code>\n\n"
            "Використовуй <code>yearly</code>, щоб повторювати щороку."
        ),
        "repeat_yearly": "щороку",
        "repeat_once": "один раз",
        "added": "✅ Нагадування додано",
        "no_reminders": "📭 У тебе немає активних нагадувань.",
        "reminders": "📅 Твої нагадування:",
        "nothing_today": "📭 На сьогодні нічого немає.",
        "deleted": "🗑 Видалено.",
        "not_found": "Не знайшов такого нагадування.",
        "past": "Цей час уже минув.",
        "use_delete": "Використовуй: /delete ID",
        "reminder": "🔔 Нагадування",
        "language_saved": "✅ Мову збережено.",
        "back": "↩️ Назад",
        "delete_hint": "Щоб видалити: /delete ID",
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
                language TEXT NOT NULL
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
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
                InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
            ],
            [
                InlineKeyboardButton(text="🇮🇹 Italiano", callback_data="lang:it"),
                InlineKeyboardButton(text="🇺🇦 Українська", callback_data="lang:uk"),
            ],
        ]
    )


def menu_keyboard(language: str):
    t = TEXT[language]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t["add"], callback_data="menu:add")],
            [
                InlineKeyboardButton(text=t["list"], callback_data="menu:list"),
                InlineKeyboardButton(text=t["today"], callback_data="menu:today"),
            ],
            [
                InlineKeyboardButton(text=t["language"], callback_data="menu:language"),
                InlineKeyboardButton(text=t["help"], callback_data="menu:help"),
            ],
        ]
    )


def back_keyboard(language: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=TEXT[language]["back"], callback_data="menu:home")]
        ]
    )


async def show_home(message: Message, language: str, edit: bool = False):
    t = TEXT[language]
    text = f"{t['welcome']}\n\n<b>{t['menu']}</b>"

    if edit:
        await message.edit_text(text, reply_markup=menu_keyboard(language))
    else:
        await message.answer(text, reply_markup=menu_keyboard(language))


def parse_reminder(text: str):
    parts = [part.strip() for part in text.split("|")]

    if len(parts) < 2 or len(parts) > 3:
        raise ValueError

    date_text, title = parts[0], parts[1]
    repeat = parts[2].lower() if len(parts) == 3 else "none"

    if repeat not in {"none", "yearly"}:
        raise ValueError

    reminder_at = datetime.strptime(
        date_text,
        "%Y-%m-%d %H:%M",
    ).replace(tzinfo=TIMEZONE)

    return reminder_at, title, repeat


@dp.message(Command("start"))
async def start(message: Message):
    language = await get_language(message.from_user.id)

    if language is None:
        await message.answer(
            "⏰ <b>Reminder Bot</b>\n\n"
            "Choose your language / Выберите язык\n"
            "Scegli la lingua / Оберіть мову:",
            reply_markup=language_keyboard(),
        )
        return

    await show_home(message, language)


@dp.callback_query(F.data.startswith("lang:"))
async def language_selected(callback: CallbackQuery):
    language = callback.data.split(":", 1)[1]

    if language not in LANGUAGES:
        await callback.answer()
        return

    await set_language(callback.from_user.id, language)
    await callback.message.edit_text(
        TEXT[language]["language_saved"],
    )
    await show_home(callback.message, language)
    await callback.answer()


@dp.callback_query(F.data == "menu:home")
async def menu_home(callback: CallbackQuery):
    language = await get_language(callback.from_user.id) or "en"
    await show_home(callback.message, language, edit=True)
    await callback.answer()


@dp.callback_query(F.data == "menu:add")
async def menu_add(callback: CallbackQuery):
    language = await get_language(callback.from_user.id) or "en"
    await callback.message.edit_text(
        TEXT[language]["add_help"],
        reply_markup=back_keyboard(language),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data == "menu:list")
async def menu_list(callback: CallbackQuery):
    language = await get_language(callback.from_user.id) or "en"

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """
            SELECT id, title, reminder_at, repeat
            FROM reminders
            WHERE telegram_id = ? AND sent_at IS NULL
            ORDER BY reminder_at
            """,
            (callback.from_user.id,),
        )
        rows = await cursor.fetchall()

    if not rows:
        text = TEXT[language]["no_reminders"]
    else:
        lines = [TEXT[language]["reminders"], ""]
        for reminder_id, title, reminder_at, repeat in rows:
            dt = datetime.fromisoformat(reminder_at).astimezone(TIMEZONE)
            repeat_text = (
                TEXT[language]["repeat_yearly"]
                if repeat == "yearly"
                else TEXT[language]["repeat_once"]
            )
            lines.append(
                f"#{reminder_id} · {dt:%d.%m.%Y %H:%M} · {title} · {repeat_text}"
            )
        lines.append("")
        lines.append(TEXT[language]["delete_hint"])
        text = "\n".join(lines)

    await callback.message.edit_text(
        text,
        reply_markup=back_keyboard(language),
    )
    await callback.answer()


@dp.callback_query(F.data == "menu:today")
async def menu_today(callback: CallbackQuery):
    language = await get_language(callback.from_user.id) or "en"
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
            (callback.from_user.id, f"{today_value}%"),
        )
        rows = await cursor.fetchall()

    if not rows:
        text = TEXT[language]["nothing_today"]
    else:
        lines = [TEXT[language]["today"], ""]
        for reminder_id, title, reminder_at in rows:
            dt = datetime.fromisoformat(reminder_at).astimezone(TIMEZONE)
            lines.append(f"#{reminder_id} · {dt:%H:%M} · {title}")
        text = "\n".join(lines)

    await callback.message.edit_text(
        text,
        reply_markup=back_keyboard(language),
    )
    await callback.answer()


@dp.callback_query(F.data == "menu:language")
async def menu_language(callback: CallbackQuery):
    language = await get_language(callback.from_user.id) or "en"
    await callback.message.edit_text(
        TEXT[language]["choose_language"],
        reply_markup=language_keyboard(),
    )
    await callback.answer()


@dp.callback_query(F.data == "menu:help")
async def menu_help(callback: CallbackQuery):
    language = await get_language(callback.from_user.id) or "en"
    await callback.message.edit_text(
        TEXT[language]["add_help"],
        reply_markup=back_keyboard(language),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.message(Command("help"))
async def help_command(message: Message):
    language = await get_language(message.from_user.id) or "en"
    await message.answer(
        TEXT[language]["add_help"],
        parse_mode="HTML",
    )


@dp.message(Command("add"))
async def add_reminder(message: Message):
    language = await get_language(message.from_user.id) or "en"
    t = TEXT[language]
    payload = message.text.removeprefix("/add").strip()

    try:
        reminder_at, title, repeat = parse_reminder(payload)
    except ValueError:
        await message.answer(t["add_help"], parse_mode="HTML")
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
        f"<b>{t['added']}</b>\n\n"
        f"📝 {title}\n"
        f"📅 {reminder_at:%d.%m.%Y}\n"
        f"⏰ {reminder_at:%H:%M}\n"
        f"🔁 {repeat_text}",
        parse_mode="HTML",
        reply_markup=menu_keyboard(language),
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
        reply_markup=menu_keyboard(language),
    )


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
                    f"<b>{TEXT[language]['reminder']}</b>\n\n📝 {title}",
                    parse_mode="HTML",
                    reply_markup=menu_keyboard(language),
                )

                if repeat == "yearly":
                    old_date = datetime.fromisoformat(reminder_at)

                    try:
                        next_date = old_date.replace(
                            year=old_date.year + 1
                        )
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
