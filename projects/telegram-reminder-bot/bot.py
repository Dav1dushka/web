import asyncio
import html
import os
from calendar import monthrange
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

DB_NAME = "reminders.db"
CHECK_EVERY_SECONDS = 30
TIMEZONE = ZoneInfo(os.getenv("BOT_TIMEZONE", "Europe/Prague"))

dp = Dispatcher(storage=MemoryStorage())


class AddReminder(StatesGroup):
    waiting_title = State()
    waiting_datetime = State()


LANGUAGES = {
    "ru": ("🇷🇺", "Русский"),
    "en": ("🇬🇧", "English"),
    "it": ("🇮🇹", "Italiano"),
    "uk": ("🇺🇦", "Українська"),
}

TEXT = {
    "ru": {
        "choose_language": "Выбери язык бота:",
        "welcome": "⏰ <b>Reminder Bot</b>\nЯ помогу не забыть важные даты и дела.",
        "menu": "Главное меню",
        "add": "➕ Добавить напоминание",
        "list": "📅 Мои напоминания",
        "today": "📌 Сегодня",
        "language": "🌐 Язык",
        "help": "ℹ️ Помощь",
        "ask_title": "📝 Напиши, что нужно напомнить.",
        "ask_datetime": "📅 Теперь введи дату и время.\nНапример: <code>27.10.2026 09:00</code>",
        "choose_repeat": "🔁 Как часто повторять?",
        "once": "Один раз",
        "daily": "Каждый день",
        "every_2_days": "Через день",
        "weekly": "Через неделю",
        "monthly": "Через месяц",
        "yearly": "Через год",
        "cancel": "✖️ Отмена",
        "added": "✅ Напоминание добавлено",
        "no_reminders": "📭 Пока нет активных напоминаний.",
        "reminders": "📅 Твои напоминания:",
        "nothing_today": "📭 На сегодня ничего нет.",
        "deleted": "🗑 Удалено.",
        "not_found": "Не нашёл такое напоминание.",
        "past": "Это время уже прошло.",
        "bad_datetime": "Не понял дату. Напиши так: <code>27.10.2026 09:00</code>",
        "language_saved": "✅ Язык сохранён.",
        "back": "↩️ Назад",
        "delete": "🗑 Удалить",
        "delete_hint": "Нажми кнопку рядом с напоминанием, чтобы удалить его.",
        "help_text": (
            "Здесь можно хранить важные даты и задачи.\n\n"
            "➕ <b>Добавить</b> — создай напоминание шаг за шагом.\n"
            "📅 <b>Мои напоминания</b> — список всех активных.\n"
            "📌 <b>Сегодня</b> — что запланировано на сегодня.\n"
            "🌐 <b>Язык</b> — сменить язык бота."
        ),
        "repeat_label": {
            "once": "один раз",
            "daily": "каждый день",
            "every_2_days": "через день",
            "weekly": "через неделю",
            "monthly": "через месяц",
            "yearly": "через год",
        },
    },
    "en": {
        "choose_language": "Choose your bot language:",
        "welcome": "⏰ <b>Reminder Bot</b>\nI'll help you remember important dates and tasks.",
        "menu": "Main menu",
        "add": "➕ Add reminder",
        "list": "📅 My reminders",
        "today": "📌 Today",
        "language": "🌐 Language",
        "help": "ℹ️ Help",
        "ask_title": "📝 What should I remind you about?",
        "ask_datetime": "📅 Now enter the date and time.\nExample: <code>27.10.2026 09:00</code>",
        "choose_repeat": "🔁 How often should it repeat?",
        "once": "Once",
        "daily": "Every day",
        "every_2_days": "Every 2 days",
        "weekly": "Every week",
        "monthly": "Every month",
        "yearly": "Every year",
        "cancel": "✖️ Cancel",
        "added": "✅ Reminder added",
        "no_reminders": "📭 You have no active reminders.",
        "reminders": "📅 Your reminders:",
        "nothing_today": "📭 Nothing planned for today.",
        "deleted": "🗑 Deleted.",
        "not_found": "I couldn't find that reminder.",
        "past": "That time is already in the past.",
        "bad_datetime": "I couldn't read the date. Use: <code>27.10.2026 09:00</code>",
        "language_saved": "✅ Language saved.",
        "back": "↩️ Back",
        "delete": "🗑 Delete",
        "delete_hint": "Use the button next to a reminder to delete it.",
        "help_text": (
            "Use this bot for important dates and tasks.\n\n"
            "➕ <b>Add reminder</b> — create one step by step.\n"
            "📅 <b>My reminders</b> — see active reminders.\n"
            "📌 <b>Today</b> — see today's reminders.\n"
            "🌐 <b>Language</b> — change the bot language."
        ),
        "repeat_label": {
            "once": "once",
            "daily": "every day",
            "every_2_days": "every 2 days",
            "weekly": "every week",
            "monthly": "every month",
            "yearly": "every year",
        },
    },
    "it": {
        "choose_language": "Scegli la lingua del bot:",
        "welcome": "⏰ <b>Reminder Bot</b>\nTi aiuterò a ricordare date e attività importanti.",
        "menu": "Menu principale",
        "add": "➕ Aggiungi promemoria",
        "list": "📅 I miei promemoria",
        "today": "📌 Oggi",
        "language": "🌐 Lingua",
        "help": "ℹ️ Aiuto",
        "ask_title": "📝 Cosa devo ricordarti?",
        "ask_datetime": "📅 Inserisci data e ora.\nEsempio: <code>27.10.2026 09:00</code>",
        "choose_repeat": "🔁 Quanto spesso ripetere?",
        "once": "Una volta",
        "daily": "Ogni giorno",
        "every_2_days": "Ogni 2 giorni",
        "weekly": "Ogni settimana",
        "monthly": "Ogni mese",
        "yearly": "Ogni anno",
        "cancel": "✖️ Annulla",
        "added": "✅ Promemoria aggiunto",
        "no_reminders": "📭 Non hai promemoria attivi.",
        "reminders": "📅 I tuoi promemoria:",
        "nothing_today": "📭 Niente in programma per oggi.",
        "deleted": "🗑 Eliminato.",
        "not_found": "Non ho trovato quel promemoria.",
        "past": "Questo orario è già passato.",
        "bad_datetime": "Formato data: <code>27.10.2026 09:00</code>",
        "language_saved": "✅ Lingua salvata.",
        "back": "↩️ Indietro",
        "delete": "🗑 Elimina",
        "delete_hint": "Usa il pulsante accanto al promemoria per eliminarlo.",
        "help_text": (
            "Usa il bot per date e attività importanti.\n\n"
            "➕ <b>Aggiungi</b> — crea un promemoria passo dopo passo.\n"
            "📅 <b>I miei promemoria</b> — mostra quelli attivi.\n"
            "📌 <b>Oggi</b> — mostra quelli di oggi.\n"
            "🌐 <b>Lingua</b> — cambia la lingua del bot."
        ),
        "repeat_label": {
            "once": "una volta",
            "daily": "ogni giorno",
            "every_2_days": "ogni 2 giorni",
            "weekly": "ogni settimana",
            "monthly": "ogni mese",
            "yearly": "ogni anno",
        },
    },
    "uk": {
        "choose_language": "Оберіть мову бота:",
        "welcome": "⏰ <b>Reminder Bot</b>\nЯ допоможу не забувати важливі дати та справи.",
        "menu": "Головне меню",
        "add": "➕ Додати нагадування",
        "list": "📅 Мої нагадування",
        "today": "📌 Сьогодні",
        "language": "🌐 Мова",
        "help": "ℹ️ Допомога",
        "ask_title": "📝 Що потрібно нагадати?",
        "ask_datetime": "📅 Введи дату та час.\nНаприклад: <code>27.10.2026 09:00</code>",
        "choose_repeat": "🔁 Як часто повторювати?",
        "once": "Один раз",
        "daily": "Щодня",
        "every_2_days": "Через день",
        "weekly": "Через тиждень",
        "monthly": "Через місяць",
        "yearly": "Через рік",
        "cancel": "✖️ Скасувати",
        "added": "✅ Нагадування додано",
        "no_reminders": "📭 У тебе немає активних нагадувань.",
        "reminders": "📅 Твої нагадування:",
        "nothing_today": "📭 На сьогодні нічого немає.",
        "deleted": "🗑 Видалено.",
        "not_found": "Не знайшов такого нагадування.",
        "past": "Цей час уже минув.",
        "bad_datetime": "Формат дати: <code>27.10.2026 09:00</code>",
        "language_saved": "✅ Мову збережено.",
        "back": "↩️ Назад",
        "delete": "🗑 Видалити",
        "delete_hint": "Натисни кнопку біля нагадування, щоб його видалити.",
        "help_text": (
            "Використовуй бота для важливих дат і справ.\n\n"
            "➕ <b>Додати</b> — створи нагадування крок за кроком.\n"
            "📅 <b>Мої нагадування</b> — список активних.\n"
            "📌 <b>Сьогодні</b> — нагадування на сьогодні.\n"
            "🌐 <b>Мова</b> — зміни мову бота."
        ),
        "repeat_label": {
            "once": "один раз",
            "daily": "щодня",
            "every_2_days": "через день",
            "weekly": "через тиждень",
            "monthly": "через місяць",
            "yearly": "щороку",
        },
    },
}


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


def repeat_keyboard(language: str):
    t = TEXT[language]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t["once"], callback_data="repeat:once"),
                InlineKeyboardButton(text=t["daily"], callback_data="repeat:daily"),
            ],
            [
                InlineKeyboardButton(text=t["every_2_days"], callback_data="repeat:every_2_days"),
                InlineKeyboardButton(text=t["weekly"], callback_data="repeat:weekly"),
            ],
            [
                InlineKeyboardButton(text=t["monthly"], callback_data="repeat:monthly"),
                InlineKeyboardButton(text=t["yearly"], callback_data="repeat:yearly"),
            ],
            [InlineKeyboardButton(text=t["cancel"], callback_data="add:cancel")],
        ]
    )


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                reminder_at TEXT NOT NULL,
                repeat TEXT NOT NULL DEFAULT 'once',
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


async def show_home(message: Message, language: str, edit: bool = False):
    text = f"{TEXT[language]['welcome']}\n\n<b>{TEXT[language]['menu']}</b>"

    if edit:
        await message.edit_text(
            text,
            reply_markup=menu_keyboard(language),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            text,
            reply_markup=menu_keyboard(language),
            parse_mode="HTML",
        )


def parse_datetime(text: str):
    return datetime.strptime(
        text.strip(),
        "%d.%m.%Y %H:%M",
    ).replace(tzinfo=TIMEZONE)


def next_occurrence(dt: datetime, repeat: str) -> datetime | None:
    if repeat == "once":
        return None

    if repeat == "daily":
        return dt + timedelta(days=1)

    if repeat == "every_2_days":
        return dt + timedelta(days=2)

    if repeat == "weekly":
        return dt + timedelta(days=7)

    if repeat == "monthly":
        next_month = 1 if dt.month == 12 else dt.month + 1
        next_year = dt.year + 1 if dt.month == 12 else dt.year
        day = min(dt.day, monthrange(next_year, next_month)[1])
        return dt.replace(year=next_year, month=next_month, day=day)

    if repeat == "yearly":
        day = dt.day
        if dt.month == 2 and dt.day == 29:
            day = 28
        return dt.replace(year=dt.year + 1, day=day)

    return None


@dp.message(Command("start"))
async def start(message: Message, state: FSMContext):
    await state.clear()

    language = await get_language(message.from_user.id)

    if language is None:
        await message.answer(
            "⏰ <b>Reminder Bot</b>\n\n"
            "Выберите язык / Choose your language\n"
            "Scegli la lingua / Оберіть мову:",
            reply_markup=language_keyboard(),
            parse_mode="HTML",
        )
        return

    await show_home(message, language)


@dp.callback_query(F.data.startswith("lang:"))
async def language_selected(callback: CallbackQuery, state: FSMContext):
    language = callback.data.split(":", 1)[1]

    if language not in LANGUAGES:
        await callback.answer()
        return

    await state.clear()
    await set_language(callback.from_user.id, language)

    await callback.message.edit_text(
        TEXT[language]["language_saved"],
        parse_mode="HTML",
    )
    await show_home(callback.message, language)
    await callback.answer()


@dp.callback_query(F.data == "menu:home")
async def menu_home(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    language = await get_language(callback.from_user.id) or "en"
    await show_home(callback.message, language, edit=True)
    await callback.answer()


@dp.callback_query(F.data == "menu:add")
async def menu_add(callback: CallbackQuery, state: FSMContext):
    language = await get_language(callback.from_user.id) or "en"
    await state.set_state(AddReminder.waiting_title)

    await callback.message.edit_text(
        f"➕ <b>{TEXT[language]['add']}</b>\n\n{TEXT[language]['ask_title']}",
        reply_markup=back_keyboard(language),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.message(AddReminder.waiting_title)
async def reminder_title(message: Message, state: FSMContext):
    language = await get_language(message.from_user.id) or "en"

    title = message.text.strip()

    if not title:
        await message.answer(TEXT[language]["ask_title"])
        return

    await state.update_data(title=title)
    await state.set_state(AddReminder.waiting_datetime)

    await message.answer(
        TEXT[language]["ask_datetime"],
        reply_markup=back_keyboard(language),
        parse_mode="HTML",
    )


@dp.message(AddReminder.waiting_datetime)
async def reminder_datetime(message: Message, state: FSMContext):
    language = await get_language(message.from_user.id) or "en"

    try:
        reminder_at = parse_datetime(message.text)
    except ValueError:
        await message.answer(
            TEXT[language]["bad_datetime"],
            parse_mode="HTML",
        )
        return

    if reminder_at <= datetime.now(TIMEZONE):
        await message.answer(TEXT[language]["past"])
        return

    await state.update_data(reminder_at=reminder_at.isoformat())
    await message.answer(
        TEXT[language]["choose_repeat"],
        reply_markup=repeat_keyboard(language),
    )


@dp.callback_query(F.data == "add:cancel")
async def cancel_add(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    language = await get_language(callback.from_user.id) or "en"
    await show_home(callback.message, language, edit=True)
    await callback.answer()


@dp.callback_query(F.data.startswith("repeat:"))
async def choose_repeat(callback: CallbackQuery, state: FSMContext):
    language = await get_language(callback.from_user.id) or "en"
    repeat = callback.data.split(":", 1)[1]

    if repeat not in TEXT[language]["repeat_label"]:
        await callback.answer()
        return

    data = await state.get_data()
    title = data.get("title")
    reminder_at = data.get("reminder_at")

    if not title or not reminder_at:
        await state.clear()
        await show_home(callback.message, language, edit=True)
        await callback.answer()
        return

    dt = datetime.fromisoformat(reminder_at)

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
                callback.from_user.id,
                title,
                dt.isoformat(),
                repeat,
            ),
        )
        await db.commit()

    await state.clear()

    safe_title = html.escape(title)
    repeat_text = TEXT[language]["repeat_label"][repeat]

    await callback.message.edit_text(
        f"<b>{TEXT[language]['added']}</b>\n\n"
        f"📝 {safe_title}\n"
        f"📅 {dt:%d.%m.%Y}\n"
        f"⏰ {dt:%H:%M}\n"
        f"🔁 {repeat_text}",
        reply_markup=menu_keyboard(language),
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
        keyboard = back_keyboard(language)
    else:
        lines = [TEXT[language]["reminders"], ""]
        buttons = []

        for reminder_id, title, reminder_at, repeat in rows:
            dt = datetime.fromisoformat(reminder_at).astimezone(TIMEZONE)
            repeat_text = TEXT[language]["repeat_label"].get(
                repeat,
                repeat,
            )
            lines.append(
                f"#{reminder_id} · {dt:%d.%m.%Y %H:%M} · "
                f"{html.escape(title)}\n"
                f"🔁 {repeat_text}"
            )
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"{TEXT[language]['delete']} #{reminder_id}",
                        callback_data=f"delete:{reminder_id}",
                    )
                ]
            )

        lines.append("")
        lines.append(TEXT[language]["delete_hint"])

        buttons.append(
            [InlineKeyboardButton(
                text=TEXT[language]["back"],
                callback_data="menu:home",
            )]
        )

        text = "\n".join(lines)
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("delete:"))
async def delete_callback(callback: CallbackQuery):
    language = await get_language(callback.from_user.id) or "en"
    reminder_id = int(callback.data.split(":", 1)[1])

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """
            DELETE FROM reminders
            WHERE id = ? AND telegram_id = ?
            """,
            (reminder_id, callback.from_user.id),
        )
        await db.commit()

    if cursor.rowcount == 0:
        await callback.answer(TEXT[language]["not_found"], show_alert=True)
        return

    await callback.answer(TEXT[language]["deleted"])
    await menu_list(callback)


@dp.callback_query(F.data == "menu:today")
async def menu_today(callback: CallbackQuery):
    language = await get_language(callback.from_user.id) or "en"
    today_value = datetime.now(TIMEZONE).date().isoformat()

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """
            SELECT id, title, reminder_at, repeat
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
        for reminder_id, title, reminder_at, repeat in rows:
            dt = datetime.fromisoformat(reminder_at).astimezone(TIMEZONE)
            lines.append(
                f"#{reminder_id} · {dt:%H:%M} · {html.escape(title)}"
            )
        text = "\n".join(lines)

    await callback.message.edit_text(
        text,
        reply_markup=back_keyboard(language),
        parse_mode="HTML",
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
        TEXT[language]["help_text"],
        reply_markup=back_keyboard(language),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.message(Command("help"))
async def help_command(message: Message):
    language = await get_language(message.from_user.id) or "en"
    await message.answer(
        TEXT[language]["help_text"],
        parse_mode="HTML",
    )


@dp.message(Command("list"))
async def list_command(message: Message):
    language = await get_language(message.from_user.id) or "en"

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
        await message.answer(TEXT[language]["no_reminders"])
        return

    lines = [TEXT[language]["reminders"], ""]

    for reminder_id, title, reminder_at, repeat in rows:
        dt = datetime.fromisoformat(reminder_at).astimezone(TIMEZONE)
        repeat_text = TEXT[language]["repeat_label"].get(repeat, repeat)
        lines.append(
            f"#{reminder_id} · {dt:%d.%m.%Y %H:%M} · {html.escape(title)}\n"
            f"🔁 {repeat_text}"
        )

    await message.answer("\n".join(lines), parse_mode="HTML")


@dp.message(Command("today"))
async def today_command(message: Message):
    language = await get_language(message.from_user.id) or "en"
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
        await message.answer(TEXT[language]["nothing_today"])
        return

    lines = [TEXT[language]["today"], ""]

    for reminder_id, title, reminder_at in rows:
        dt = datetime.fromisoformat(reminder_at).astimezone(TIMEZONE)
        lines.append(f"#{reminder_id} · {dt:%H:%M} · {html.escape(title)}")

    await message.answer("\n".join(lines), parse_mode="HTML")


@dp.message(Command("delete"))
async def delete_command(message: Message):
    language = await get_language(message.from_user.id) or "en"
    payload = message.text.removeprefix("/delete").strip()

    try:
        reminder_id = int(payload)
    except ValueError:
        await message.answer("/delete ID")
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
        await message.answer(TEXT[language]["not_found"])
        return

    await message.answer(TEXT[language]["deleted"])


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
                safe_title = html.escape(title)

                await bot.send_message(
                    telegram_id,
                    f"<b>{TEXT[language]['reminder']}</b>\n\n📝 {safe_title}",
                    parse_mode="HTML",
                    reply_markup=menu_keyboard(language),
                )

                next_date = next_occurrence(
                    datetime.fromisoformat(reminder_at),
                    repeat,
                )

                if next_date is None:
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
                else:
                    await db.execute(
                        """
                        UPDATE reminders
                        SET reminder_at = ?
                        WHERE id = ?
                        """,
                        (next_date.isoformat(), reminder_id),
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
