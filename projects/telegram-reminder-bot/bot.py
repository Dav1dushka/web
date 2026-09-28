import asyncio
import calendar
import html
import os
import re
import tempfile
from calendar import monthrange
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, Message

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

DB = "reminders.db"
DEFAULT_TZ = os.getenv("BOT_TIMEZONE", "Europe/Prague")
CHECK = 30
dp = Dispatcher(storage=MemoryStorage())


class Add(StatesGroup):
    title = State()
    category = State()
    priority = State()
    date = State()
    time = State()
    repeat = State()
    lead = State()
    weekdays = State()


class Edit(StatesGroup):
    title = State()
    dt = State()


class Smart(StatesGroup):
    text = State()


class Search(StatesGroup):
    text = State()


LANGS = {"ru": ("🇷🇺", "Русский"), "en": ("🇬🇧", "English"), "it": ("🇮🇹", "Italiano"), "uk": ("🇺🇦", "Українська")}
CAT = {
    "birthday": ("🎂", {"ru": "Дни рождения", "en": "Birthdays", "it": "Compleanni", "uk": "Дні народження"}),
    "work": ("💼", {"ru": "Работа", "en": "Work", "it": "Lavoro", "uk": "Робота"}),
    "study": ("📚", {"ru": "Учёба", "en": "Study", "it": "Studio", "uk": "Навчання"}),
    "payment": ("💳", {"ru": "Платежи", "en": "Payments", "it": "Pagamenti", "uk": "Платежі"}),
    "trip": ("✈️", {"ru": "Поездки", "en": "Trips", "it": "Viaggi", "uk": "Поїздки"}),
    "task": ("📝", {"ru": "Задачи", "en": "Tasks", "it": "Attività", "uk": "Завдання"}),
    "health": ("💊", {"ru": "Здоровье", "en": "Health", "it": "Salute", "uk": "Здоров'я"}),
    "other": ("📌", {"ru": "Другое", "en": "Other", "it": "Altro", "uk": "Інше"}),
}
TZS = {"prague": ("🇨🇿 Europe/Prague", "Europe/Prague"), "rome": ("🇮🇹 Europe/Rome", "Europe/Rome"), "kyiv": ("🇺🇦 Europe/Kyiv", "Europe/Kyiv"), "utc": ("🌍 UTC", "UTC")}

UI = {
"ru":{"welcome":"⏰ <b>Reminder Bot</b>\nЯ помогу не забыть важные даты и дела.","menu":"Главное меню","add":"➕ Добавить","list":"📅 Мои","today":"📌 Сегодня","lang":"🌐 Язык","help":"ℹ️ Помощь","settings":"⚙️ Настройки","smart":"✨ Умный ввод","export":"📤 Экспорт","title":"📝 Что напомнить?","cat":"🏷 Категория","dt":"📅 Дата и время: <code>27.10.2026 09:00</code>","repeat":"🔁 Повтор","once":"Один раз","daily":"Каждый день","2d":"Через 2 дня","week":"Через неделю","month":"Через месяц","year":"Через год","cancel":"✖️ Отмена","added":"✅ Добавлено","empty":"📭 Пока пусто.","deleted":"🗑 Удалено.","notfound":"Не найдено.","past":"Это время уже прошло.","choose_minutes":"⏱ Выбери минуты","custom_time":"✏️ Ввести своё время","custom_time_prompt":"⌨️ Напиши время в формате HH:MM, например 18:35.","custom_time_invalid":"Нужно написать время в формате HH:MM, например 08:05.","back":"↩️ Назад","edit":"✏️ Изменить","share":"🔗 Поделиться","snooze10":"⏰ 10 мин","snooze60":"⏰ 1 час","snooze1440":"📅 Завтра","done":"✅ Готово","settings_title":"⚙️ Настройки","tz":"🌍 Часовой пояс","digest":"🌅 Утренний обзор","digest_on":"✅ Обзор включён на 09:00.","digest_off":"Обзор выключен.","choose_tz":"Выбери часовой пояс","tz_saved":"✅ Сохранено.","smart_prompt":"✨ Напиши обычной фразой, например: <code>через 3 дня в 19:00 купить подарок маме</code>","help_text":"➕ Добавляй напоминания шаг за шагом.\n✨ Умный ввод понимает обычные фразы.\n🔔 После уведомления можно отложить его.\n📤 Экспорт создаёт .ics для календаря.\n🔗 Поделиться даёт ссылку для общего напоминания.","digest_title":"🌅 Сегодня","nothing":"На сегодня ничего нет.","repeat_names":{"once":"разово","daily":"ежедневно","2d":"раз в 2 дня","week":"еженедельно","month":"ежемесячно","year":"ежегодно"},"lang_saved":"✅ Язык сохранён."},
"en":{"welcome":"⏰ <b>Reminder Bot</b>\nI'll help you remember important dates and tasks.","menu":"Main menu","add":"➕ Add","list":"📅 My reminders","today":"📌 Today","lang":"🌐 Language","help":"ℹ️ Help","settings":"⚙️ Settings","smart":"✨ Smart input","export":"📤 Export","title":"📝 What should I remind you about?","cat":"🏷 Category","dt":"📅 Date and time: <code>27.10.2026 09:00</code>","repeat":"🔁 Repeat","once":"Once","daily":"Every day","2d":"Every 2 days","week":"Every week","month":"Every month","year":"Every year","cancel":"✖️ Cancel","added":"✅ Added","empty":"📭 Nothing here yet.","deleted":"🗑 Deleted.","notfound":"Not found.","past":"That time is already in the past.","choose_minutes":"⏱ Choose minutes","custom_time":"✏️ Enter custom time","custom_time_prompt":"⌨️ Type the time as HH:MM, for example 18:35.","custom_time_invalid":"Use HH:MM format, for example 08:05.","back":"↩️ Back","edit":"✏️ Edit","share":"🔗 Share","snooze10":"⏰ 10 min","snooze60":"⏰ 1 hour","snooze1440":"📅 Tomorrow","done":"✅ Done","settings_title":"⚙️ Settings","tz":"🌍 Time zone","digest":"🌅 Morning digest","digest_on":"✅ Digest enabled for 09:00.","digest_off":"Digest disabled.","choose_tz":"Choose your time zone","tz_saved":"✅ Saved.","smart_prompt":"✨ Write naturally, for example: <code>in 3 days at 19:00 buy a gift for mom</code>","help_text":"➕ Add reminders step by step.\n✨ Smart input understands normal phrases.\n🔔 Snooze notifications.\n📤 Export .ics.\n🔗 Share reminders with someone else.","digest_title":"🌅 Today","nothing":"Nothing planned for today.","repeat_names":{"once":"once","daily":"daily","2d":"every 2 days","week":"weekly","month":"monthly","year":"yearly"},"lang_saved":"✅ Language saved."},
"it":{"welcome":"⏰ <b>Reminder Bot</b>\nTi aiuterò a ricordare date e attività importanti.","menu":"Menu principale","add":"➕ Aggiungi","list":"📅 I miei","today":"📌 Oggi","lang":"🌐 Lingua","help":"ℹ️ Aiuto","settings":"⚙️ Impostazioni","smart":"✨ Input smart","export":"📤 Esporta","title":"📝 Cosa devo ricordarti?","cat":"🏷 Categoria","dt":"📅 Data e ora: <code>27.10.2026 09:00</code>","repeat":"🔁 Ripetizione","once":"Una volta","daily":"Ogni giorno","2d":"Ogni 2 giorni","week":"Ogni settimana","month":"Ogni mese","year":"Ogni anno","cancel":"✖️ Annulla","added":"✅ Aggiunto","empty":"📭 Ancora niente.","deleted":"🗑 Eliminato.","notfound":"Non trovato.","past":"Questo orario è già passato.","back":"↩️ Indietro","edit":"✏️ Modifica","share":"🔗 Condividi","snooze10":"⏰ 10 min","snooze60":"⏰ 1 ora","snooze1440":"📅 Domani","done":"✅ Fatto","settings_title":"⚙️ Impostazioni","tz":"🌍 Fuso orario","digest":"🌅 Riepilogo","digest_on":"✅ Riepilogo attivo alle 09:00.","digest_off":"Riepilogo disattivato.","choose_tz":"Scegli il fuso orario","tz_saved":"✅ Salvato.","smart_prompt":"✨ Scrivi in modo naturale, per esempio: <code>tra 3 giorni alle 19:00 compra un regalo per mamma</code>","help_text":"➕ Aggiungi passo dopo passo.\n✨ Input smart per frasi normali.\n🔔 Posticipa le notifiche.\n📤 Esporta .ics.\n🔗 Condividi promemoria.","digest_title":"🌅 Oggi","nothing":"Niente per oggi.","repeat_names":{"once":"una volta","daily":"giornaliero","2d":"ogni 2 giorni","week":"settimanale","month":"mensile","year":"annuale"},"lang_saved":"✅ Lingua salvata."},
"uk":{"welcome":"⏰ <b>Reminder Bot</b>\nЯ допоможу не забувати важливі дати та справи.","menu":"Головне меню","add":"➕ Додати","list":"📅 Мої","today":"📌 Сьогодні","lang":"🌐 Мова","help":"ℹ️ Допомога","settings":"⚙️ Налаштування","smart":"✨ Розумний ввід","export":"📤 Експорт","title":"📝 Що потрібно нагадати?","cat":"🏷 Категорія","dt":"📅 Дата і час: <code>27.10.2026 09:00</code>","repeat":"🔁 Повтор","once":"Один раз","daily":"Щодня","2d":"Через 2 дні","week":"Щотижня","month":"Щомісяця","year":"Щороку","cancel":"✖️ Скасувати","added":"✅ Додано","empty":"📭 Поки порожньо.","deleted":"🗑 Видалено.","notfound":"Не знайдено.","past":"Цей час уже минув.","choose_minutes":"⏱ Обери хвилини","custom_time":"✏️ Ввести свій час","custom_time_prompt":"⌨️ Введи час у форматі HH:MM, наприклад 18:35.","custom_time_invalid":"Використай формат HH:MM, наприклад 08:05.","back":"↩️ Назад","edit":"✏️ Змінити","share":"🔗 Поділитися","snooze10":"⏰ 10 хв","snooze60":"⏰ 1 год","snooze1440":"📅 Завтра","done":"✅ Готово","settings_title":"⚙️ Налаштування","tz":"🌍 Часовий пояс","digest":"🌅 Ранковий огляд","digest_on":"✅ Огляд увімкнено на 09:00.","digest_off":"Огляд вимкнено.","choose_tz":"Обери часовий пояс","tz_saved":"✅ Збережено.","smart_prompt":"✨ Напиши звичайною фразою, наприклад: <code>через 3 дні о 19:00 купити подарунок мамі</code>","help_text":"➕ Додавай крок за кроком.\n✨ Розумний ввід розуміє звичайні фрази.\n🔔 Відкладай нагадування.\n📤 Експорт .ics.\n🔗 Ділися нагадуваннями.","digest_title":"🌅 Сьогодні","nothing":"На сьогодні нічого немає.","repeat_names":{"once":"разово","daily":"щодня","2d":"раз на 2 дні","week":"щотижня","month":"щомісяця","year":"щорічно"},"lang_saved":"✅ Мову збережено."}
}


EXTRA_UI={"ru":{"search":"🔎 Поиск","done_list":"✅ Выполненные","archive":"🗄 Архив","stats":"📊 Статистика","profile":"👤 Профиль","priority":"🎯 Приоритет","lead":"🔔 Заранее","calendar":"📅 Выбери дату","time":"⏰ Выбери время","weekdays":"📆 По дням недели","choose_days":"Выбери дни недели","completed":"✅ Выполненные","archived":"🗄 Архив","stats_title":"📊 Статистика","profile_title":"👤 Профиль","lead_values":{"0":"В момент","10":"За 10 мин","60":"За 1 час","1440":"За 1 день","10080":"За неделю"},"priority_values":{"high":"🔴 Высокий","medium":"🟡 Средний","low":"🟢 Низкий"}},"en":{"search":"🔎 Search","done_list":"✅ Completed","archive":"🗄 Archive","stats":"📊 Stats","profile":"👤 Profile","priority":"🎯 Priority","lead":"🔔 Notify before","calendar":"📅 Choose a date","time":"⏰ Choose a time","weekdays":"📆 Days of week","choose_days":"Choose weekdays","completed":"✅ Completed","archived":"🗄 Archive","stats_title":"📊 Stats","profile_title":"👤 Profile","lead_values":{"0":"At event","10":"10 min before","60":"1 hour before","1440":"1 day before","10080":"1 week before"},"priority_values":{"high":"🔴 High","medium":"🟡 Medium","low":"🟢 Low"}},"it":{"search":"🔎 Cerca","done_list":"✅ Completati","archive":"🗄 Archivio","stats":"📊 Statistiche","profile":"👤 Profilo","priority":"🎯 Priorità","lead":"🔔 Avvisa prima","calendar":"📅 Scegli la data","time":"⏰ Scegli l'ora","weekdays":"📆 Giorni","choose_days":"Scegli i giorni","completed":"✅ Completati","archived":"🗄 Archivio","stats_title":"📊 Statistiche","profile_title":"👤 Profilo","lead_values":{"0":"All'evento","10":"10 min prima","60":"1 ora prima","1440":"1 giorno prima","10080":"1 settimana prima"},"priority_values":{"high":"🔴 Alta","medium":"🟡 Media","low":"🟢 Bassa"}},"uk":{"search":"🔎 Пошук","done_list":"✅ Виконані","archive":"🗄 Архів","stats":"📊 Статистика","profile":"👤 Профіль","priority":"🎯 Пріоритет","lead":"🔔 Повідомити за","calendar":"📅 Обери дату","time":"⏰ Обери час","weekdays":"📆 Дні тижня","choose_days":"Обери дні","completed":"✅ Виконані","archived":"🗄 Архів","stats_title":"📊 Статистика","profile_title":"👤 Профіль","lead_values":{"0":"У момент","10":"За 10 хв","60":"За 1 год","1440":"За 1 день","10080":"За тиждень"},"priority_values":{"high":"🔴 Високий","medium":"🟡 Середній","low":"🟢 Низький"}}}
def texts(lang):
    x=dict(UI.get(lang,UI["en"])); x.update(EXTRA_UI.get(lang,{})); return x


def lang_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"), InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en")],
        [InlineKeyboardButton(text="🇮🇹 Italiano", callback_data="lang:it"), InlineKeyboardButton(text="🇺🇦 Українська", callback_data="lang:uk")],
    ])


def main_kb(lang):
    t=texts(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["add"], callback_data="menu:add")],
        [InlineKeyboardButton(text=t["list"], callback_data="menu:list"), InlineKeyboardButton(text=t["today"], callback_data="menu:today")],
        [InlineKeyboardButton(text=t["search"], callback_data="menu:search"), InlineKeyboardButton(text=t["smart"], callback_data="menu:smart")],
        [InlineKeyboardButton(text=t["done_list"], callback_data="menu:done"), InlineKeyboardButton(text=t["archive"], callback_data="menu:archive")],
        [InlineKeyboardButton(text=t["stats"], callback_data="menu:stats"), InlineKeyboardButton(text=t["profile"], callback_data="menu:profile")],
        [InlineKeyboardButton(text=t["settings"], callback_data="menu:settings"), InlineKeyboardButton(text=t["export"], callback_data="menu:export")],
        [InlineKeyboardButton(text=t["lang"], callback_data="menu:lang"), InlineKeyboardButton(text=t["help"], callback_data="menu:help")],
    ])


def back_kb(lang):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=texts(lang)["back"], callback_data="menu:home")]])


def cat_kb(lang):
    rows, row = [], []
    for k, (e, labels) in CAT.items():
        row.append(InlineKeyboardButton(text=f"{e} {labels[lang]}", callback_data=f"cat:{k}"))
        if len(row) == 2:
            rows.append(row); row=[]
    if row: rows.append(row)
    rows.append([InlineKeyboardButton(text=texts(lang)["cancel"], callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def repeat_kb(lang):
    t = texts(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["once"], callback_data="rep:once"), InlineKeyboardButton(text=t["daily"], callback_data="rep:daily")],
        [InlineKeyboardButton(text=t["2d"], callback_data="rep:2d"), InlineKeyboardButton(text=t["week"], callback_data="rep:week")],
        [InlineKeyboardButton(text=t["month"], callback_data="rep:month"), InlineKeyboardButton(text=t["year"], callback_data="rep:year")],
        [InlineKeyboardButton(text=t["weekdays"], callback_data="rep:weekdays")],
        [InlineKeyboardButton(text=t["cancel"], callback_data="cancel")],
    ])


def action_kb(lang, rid):
    t = texts(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["snooze10"], callback_data=f"snooze:10:{rid}"), InlineKeyboardButton(text=t["snooze60"], callback_data=f"snooze:60:{rid}")],
        [InlineKeyboardButton(text=t["snooze1440"], callback_data=f"snooze:1440:{rid}"), InlineKeyboardButton(text=t["done"], callback_data=f"done:{rid}")],
    ])


def list_actions(lang, rid):
    t = texts(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{t['edit']} #{rid}", callback_data=f"edit:{rid}"), InlineKeyboardButton(text=f"{t['delete']} #{rid}", callback_data=f"delete:{rid}")],
        [InlineKeyboardButton(text=f"{t['share']} #{rid}", callback_data=f"share:{rid}")],
    ])


def settings_kb(lang, digest):
    t=texts(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["tz"], callback_data="settings:tz")],
        [InlineKeyboardButton(text=f"{t['digest']} {'✅' if digest else '❌'}", callback_data="settings:digest")],
        [InlineKeyboardButton(text=t["back"], callback_data="menu:home")],
    ])


def tz_kb(lang):
    return InlineKeyboardMarkup(inline_keyboard=[
        *[[InlineKeyboardButton(text=label, callback_data=f"tz:{key}")] for key,(label,_) in TZS.items()],
        [InlineKeyboardButton(text=texts(lang)["back"], callback_data="menu:settings")]
    ])




def priority_kb(lang):
    t=texts(lang); return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t["priority_values"]["high"],callback_data="priority:high")],[InlineKeyboardButton(text=t["priority_values"]["medium"],callback_data="priority:medium")],[InlineKeyboardButton(text=t["priority_values"]["low"],callback_data="priority:low")],[InlineKeyboardButton(text=t["cancel"],callback_data="cancel")]])

def lead_kb(lang):
    t=texts(lang); return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t["lead_values"]["0"],callback_data="lead:0")],[InlineKeyboardButton(text=t["lead_values"]["10"],callback_data="lead:10"),InlineKeyboardButton(text=t["lead_values"]["60"],callback_data="lead:60")],[InlineKeyboardButton(text=t["lead_values"]["1440"],callback_data="lead:1440"),InlineKeyboardButton(text=t["lead_values"]["10080"],callback_data="lead:10080")]])

def calendar_kb(lang,year,month):
    rows=[[InlineKeyboardButton(text="‹",callback_data=f"calnav:{year}:{month}:prev"),InlineKeyboardButton(text=f"{year}-{month:02d}",callback_data="noop"),InlineKeyboardButton(text="›",callback_data=f"calnav:{year}:{month}:next")]]
    for week in calendar.monthcalendar(year,month): rows.append([InlineKeyboardButton(text=" " if d==0 else str(d),callback_data="noop" if d==0 else f"calday:{year:04d}-{month:02d}-{d:02d}") for d in week])
    rows.append([InlineKeyboardButton(text=texts(lang)["cancel"],callback_data="cancel")]); return InlineKeyboardMarkup(inline_keyboard=rows)

def hour_kb(lang):
    rows = []
    for start in range(0, 24, 4):
        rows.append([
            InlineKeyboardButton(text=f"{hour:02d}:00", callback_data=f"hour:{hour:02d}")
            for hour in range(start, start + 4)
        ])
    rows.append([
        InlineKeyboardButton(text=texts(lang)["custom_time"], callback_data="time:custom"),
    ])
    rows.append([
        InlineKeyboardButton(text=texts(lang)["cancel"], callback_data="cancel"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def minute_kb(lang, hour):
    values = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]
    rows = []
    for start in range(0, len(values), 4):
        rows.append([
            InlineKeyboardButton(
                text=f"{hour:02d}:{minute:02d}",
                callback_data=f"minute:{hour:02d}:{minute:02d}",
            )
            for minute in values[start:start + 4]
        ])
    rows.append([
        InlineKeyboardButton(text=texts(lang)["custom_time"], callback_data="time:custom"),
    ])
    rows.append([
        InlineKeyboardButton(text=texts(lang)["cancel"], callback_data="cancel"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def weekday_kb(lang,selected):
    labels=["Пн","Вт","Ср","Чт","Пт","Сб","Вс"] if lang=="ru" else ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]; rows=[[InlineKeyboardButton(text=("✅ " if i in selected else "")+labels[i],callback_data=f"weekday:{i}")] for i in range(7)]; rows.append([InlineKeyboardButton(text=texts(lang)["saved"],callback_data="weekday:save")]); rows.append([InlineKeyboardButton(text=texts(lang)["cancel"],callback_data="cancel")]); return InlineKeyboardMarkup(inline_keyboard=rows)

async def db_init():
    async with aiosqlite.connect(DB) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS users (telegram_id INTEGER PRIMARY KEY, language TEXT NOT NULL DEFAULT 'en', timezone TEXT NOT NULL DEFAULT 'Europe/Prague', digest_enabled INTEGER NOT NULL DEFAULT 0, digest_hour INTEGER NOT NULL DEFAULT 9, last_digest_date TEXT)")
        await db.execute("CREATE TABLE IF NOT EXISTS reminders (id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id INTEGER NOT NULL, title TEXT NOT NULL, reminder_at TEXT NOT NULL, repeat TEXT NOT NULL DEFAULT 'once', category TEXT NOT NULL DEFAULT 'other', priority TEXT NOT NULL DEFAULT 'medium', lead_minutes TEXT NOT NULL DEFAULT '0', status TEXT NOT NULL DEFAULT 'active', notified_leads TEXT NOT NULL DEFAULT '', sent_at TEXT, share_token TEXT)")
        await db.execute("CREATE TABLE IF NOT EXISTS shared_members (reminder_id INTEGER NOT NULL, telegram_id INTEGER NOT NULL, joined_at TEXT NOT NULL, PRIMARY KEY(reminder_id, telegram_id))")
        for table,col,definition in [
            ("reminders","category","TEXT NOT NULL DEFAULT 'other'"),
            ("reminders","share_token","TEXT"),
            ("reminders","priority","TEXT NOT NULL DEFAULT 'medium'"),
            ("reminders","lead_minutes","TEXT NOT NULL DEFAULT '0'"),
            ("reminders","status","TEXT NOT NULL DEFAULT 'active'"),
            ("reminders","notified_leads","TEXT NOT NULL DEFAULT ''"),
            ("users","timezone",f"TEXT NOT NULL DEFAULT '{DEFAULT_TZ}'"),
            ("users","digest_enabled","INTEGER NOT NULL DEFAULT 0"),
            ("users","digest_hour","INTEGER NOT NULL DEFAULT 9"),
            ("users","last_digest_date","TEXT")
        ]:
            c=await db.execute(f"PRAGMA table_info({table})")
            cols={r[1] for r in await c.fetchall()}
            if col not in cols:
                await db.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")
        await db.commit()


async def user(uid):
    async with aiosqlite.connect(DB) as db:
        c=await db.execute("SELECT language,timezone,digest_enabled,digest_hour,last_digest_date FROM users WHERE telegram_id=?",(uid,))
        r=await c.fetchone()
    if not r: return {"language":"en","timezone":DEFAULT_TZ,"digest_enabled":0,"digest_hour":9,"last_digest_date":None}
    return {"language":r[0],"timezone":r[1],"digest_enabled":r[2],"digest_hour":r[3],"last_digest_date":r[4]}


async def set_lang(uid, lang):
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT INTO users(telegram_id,language,timezone) VALUES(?,?,?) ON CONFLICT(telegram_id) DO UPDATE SET language=excluded.language",(uid,lang,DEFAULT_TZ))
        await db.commit()


def tz_of(u):
    try: return ZoneInfo(u["timezone"])
    except: return ZoneInfo(DEFAULT_TZ)


async def home(msg, lang, edit=False):
    text=f"{texts(lang)['welcome']}\n\n<b>{texts(lang)['menu']}</b>"
    if edit: await msg.edit_text(text, reply_markup=main_kb(lang), parse_mode="HTML")
    else: await msg.answer(text, reply_markup=main_kb(lang), parse_mode="HTML")


def parse_dt(s,tz):
    return datetime.strptime(s.strip(),"%d.%m.%Y %H:%M").replace(tzinfo=tz)

parse_datetime = parse_dt


def next_dt(dt, repeat):
    if repeat=="once": return None
    if repeat=="daily": return dt+timedelta(days=1)
    if repeat=="2d": return dt+timedelta(days=2)
    if repeat=="week": return dt+timedelta(days=7)
    if repeat=="month":
        m=1 if dt.month==12 else dt.month+1; y=dt.year+1 if dt.month==12 else dt.year
        return dt.replace(year=y,month=m,day=min(dt.day,monthrange(y,m)[1]))
    if repeat=="year":
        return dt.replace(year=dt.year+1,day=28 if dt.month==2 and dt.day==29 else dt.day)
    return None


def parse_smart(text,tz):
    now=datetime.now(tz)
    tm=re.search(r"\b(?:в|о|at|alle|о)\s*(\d{1,2})(?::(\d{2}))?\b", text.lower())
    hour=int(tm.group(1)) if tm else 9
    minute=int(tm.group(2) or 0) if tm else 0
    pats=[
        (r"(?:через|after|in|tra)\s+(\d+)\s*(?:дн|дня|дней|days?|giorni|дні)","day"),
        (r"(?:через|after|in|tra)\s+(\d+)\s*(?:нед|неделю|недель|weeks?|settimane|тиж\w+)","week"),
        (r"(?:через|after|in|tra)\s+(\d+)\s*(?:месяц|месяца|месяцев|months?|mesi|місяц\w+)","month"),
        (r"(?:через|after|in|tra)\s+(\d+)\s*(?:год|года|годов|years?|anni|рок\w+)","year"),
    ]
    for pat,unit in pats:
        m=re.search(pat,text.lower())
        if not m: continue
        n=int(m.group(1)); title=re.sub(pat,"",text,flags=re.I).strip(" ,")
        if unit=="day": target=now+timedelta(days=n)
        elif unit=="week": target=now+timedelta(days=7*n)
        elif unit=="month":
            x=now.month-1+n; y=now.year+x//12; mo=x%12+1; target=now.replace(year=y,month=mo,day=min(now.day,monthrange(y,mo)[1]))
        else: target=now.replace(year=now.year+n,day=28 if now.month==2 and now.day==29 else now.day)
        return target.replace(hour=hour,minute=minute,second=0,microsecond=0),title or text
    m=re.search(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b",text)
    if m:
        d,mo,y=map(int,m.groups()); target=datetime(y,mo,d,hour,minute,tzinfo=tz)
        return target,text.replace(m.group(0),"").strip(" ,")
    return None


async def ai_parse(text,tz,lang):
    local=parse_smart(text,tz)
    key=os.getenv("OPENAI_API_KEY")
    if not key or AsyncOpenAI is None:
        return local, False
    client=AsyncOpenAI(api_key=key)
    model=os.getenv("OPENAI_MODEL","gpt-4.1-mini")
    prompt=("Return JSON with title, datetime, repeat, category. repeat=once,daily,2d,week,month,year; "
            "category=birthday,work,study,payment,trip,task,health,other. "
            f"Now={datetime.now(tz):%Y-%m-%d %H:%M}; timezone={tz.key}; text={text}")
    r=await client.chat.completions.create(model=model,messages=[{"role":"system","content":"Parse a reminder."},{"role":"user","content":prompt}],temperature=0,response_format={"type":"json_object"})
    d=r.choices[0].message.content
    import json
    d=json.loads(d)
    dt=datetime.fromisoformat(d["datetime"]).replace(tzinfo=tz)
    return (dt,d["title"],d.get("repeat","once"),d.get("category","other")), True


async def recipients(rid,owner):
    async with aiosqlite.connect(DB) as db:
        c=await db.execute("SELECT telegram_id FROM shared_members WHERE reminder_id=?",(rid,))
        rows=await c.fetchall()
    return list({owner,*[x[0] for x in rows]})


async def export_ics(uid):
    async with aiosqlite.connect(DB) as db:
        c=await db.execute("SELECT DISTINCT r.id,r.title,r.reminder_at,r.repeat FROM reminders r LEFT JOIN shared_members s ON s.reminder_id=r.id WHERE r.telegram_id=? OR s.telegram_id=? ORDER BY r.reminder_at",(uid,uid))
        rows=await c.fetchall()
    out=["BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//Davyd//ReminderBot//EN"]
    for rid,title,dt,rep in rows:
        u=datetime.fromisoformat(dt).astimezone(timezone.utc)
        out += ["BEGIN:VEVENT",f"UID:{rid}@reminderbot",f"DTSTAMP:{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}",f"DTSTART:{u:%Y%m%dT%H%M%SZ}",f"SUMMARY:{title.replace(',','\\,').replace(';','\\;')}"]
        rr={"daily":"RRULE:FREQ=DAILY","2d":"RRULE:FREQ=DAILY;INTERVAL=2","week":"RRULE:FREQ=WEEKLY","month":"RRULE:FREQ=MONTHLY","year":"RRULE:FREQ=YEARLY"}.get(rep)
        if rr: out.append(rr)
        out.append("END:VEVENT")
    out.append("END:VCALENDAR")
    path=os.path.join(tempfile.gettempdir(),f"reminders_{uid}.ics")
    open(path,"w",encoding="utf-8").write("\r\n".join(out))
    return path


@dp.message(Command("start"))
async def start(m:Message,state:FSMContext):
    await state.clear()
    parts=(m.text or "").split(maxsplit=1)
    share_token=parts[1].removeprefix("share_") if len(parts)==2 else None
    lang=(await user(m.from_user.id))["language"]
    if not await has_user(m.from_user.id):
        if share_token:
            await state.update_data(pending_share=share_token)
        await m.answer("⏰ <b>Reminder Bot</b>\n\nВыберите язык / Choose your language / Scegli la lingua / Оберіть мову:",reply_markup=lang_kb(),parse_mode="HTML"); return
    if share_token:
        await share_join(share_token,m.from_user.id)
    await home(m,lang)


async def has_user(uid):
    async with aiosqlite.connect(DB) as db:
        c=await db.execute("SELECT 1 FROM users WHERE telegram_id=?",(uid,))
        return await c.fetchone() is not None


@dp.callback_query(F.data.startswith("lang:"))
async def lang_cb(c:CallbackQuery,state:FSMContext):
    lang=c.data.split(":")[1]
    data=await state.get_data()
    await set_lang(c.from_user.id,lang)
    await state.clear()
    await c.message.edit_text(texts(lang)["lang_saved"])
    if data.get("pending_share"):
        await share_join(data["pending_share"],c.from_user.id)
    await home(c.message,lang)
    await c.answer()


@dp.callback_query(F.data=="menu:home")
async def home_cb(c:CallbackQuery,state:FSMContext):
    await state.clear(); lang=(await user(c.from_user.id))["language"]; await home(c.message,lang,True); await c.answer()


@dp.callback_query(F.data=="menu:add")
async def add_cb(c:CallbackQuery,state:FSMContext):
    lang=(await user(c.from_user.id))["language"]; await state.set_state(Add.title)
    await c.message.edit_text(texts(lang)["title"],reply_markup=back_kb(lang)); await c.answer()


@dp.message(Add.title)
async def add_title(m:Message,state:FSMContext):
    lang=(await user(m.from_user.id))["language"]; await state.update_data(title=m.text.strip()); await state.set_state(Add.category)
    await m.answer(texts(lang)["cat"],reply_markup=cat_kb(lang))


@dp.callback_query(Add.category,F.data.startswith("cat:"))
async def add_cat(c:CallbackQuery,state:FSMContext):
    lang=(await user(c.from_user.id))["language"]; await state.update_data(category=c.data.split(":")[1]); await state.set_state(Add.priority)
    await c.message.edit_text(texts(lang)["priority"],reply_markup=priority_kb(lang)); await c.answer()


@dp.callback_query(Add.priority,F.data.startswith("priority:"))
async def add_priority(c:CallbackQuery,state:FSMContext):
    lang=(await user(c.from_user.id))["language"]; await state.update_data(priority=c.data.split(":")[1])
    tz=tz_of(await user(c.from_user.id)); now=datetime.now(tz); await state.set_state(Add.date)
    await c.message.edit_text(texts(lang)["calendar"],reply_markup=calendar_kb(lang,now.year,now.month)); await c.answer()


@dp.callback_query(Add.date,F.data.startswith("calnav:"))
async def cal_nav(c:CallbackQuery,state:FSMContext):
    _,y,m,direction=c.data.split(":"); y=int(y); m=int(m)
    if direction=="prev": m-=1; y=y-1 if m==0 else y; m=12 if m==0 else m
    else: m+=1; y=y+1 if m==13 else y; m=1 if m==13 else m
    lang=(await user(c.from_user.id))["language"]; await c.message.edit_reply_markup(reply_markup=calendar_kb(lang,y,m)); await c.answer()


@dp.callback_query(Add.date,F.data.startswith("calday:"))
async def cal_day(c:CallbackQuery,state:FSMContext):
    await state.update_data(date=c.data.split(":",1)[1]); lang=(await user(c.from_user.id))["language"]; await state.set_state(Add.time)
    await c.message.edit_text(texts(lang)["time"],reply_markup=hour_kb(lang)); await c.answer()


@dp.callback_query(Add.time,F.data=="time:custom")
async def custom_time(c:CallbackQuery,state:FSMContext):
    lang=(await user(c.from_user.id))["language"]
    await c.message.edit_text(texts(lang)["custom_time_prompt"],reply_markup=back_kb(lang))
    await c.answer()


@dp.callback_query(Add.time,F.data.startswith("hour:"))
async def choose_hour(c:CallbackQuery,state:FSMContext):
    lang=(await user(c.from_user.id))["language"]
    hour=int(c.data.split(":")[1])
    await state.update_data(hour=hour)
    await c.message.edit_text(texts(lang)["choose_minutes"],reply_markup=minute_kb(lang,hour))
    await c.answer()


@dp.callback_query(Add.time,F.data.startswith("minute:"))
async def choose_minute(c:CallbackQuery,state:FSMContext):
    data=await state.get_data()
    u=await user(c.from_user.id)
    tz=tz_of(u)
    lang=u["language"]

    _, hour_text, minute_text = c.data.split(":")
    value=f"{hour_text}:{minute_text}"
    dt=datetime.fromisoformat(f"{data['date']}T{value}:00").replace(tzinfo=tz)

    if dt <= datetime.now(tz):
        await c.answer(texts(lang)["past"], show_alert=True)
        return

    await state.update_data(dt=dt.isoformat())
    await state.set_state(Add.repeat)
    await c.message.edit_text(texts(lang)["repeat"],reply_markup=repeat_kb(lang))
    await c.answer()


@dp.message(Add.time)
async def manual_time(message:Message,state:FSMContext):
    u=await user(message.from_user.id)
    lang=u["language"]
    raw=(message.text or "").strip()

    try:
        value=datetime.strptime(raw,"%H:%M").strftime("%H:%M")
    except ValueError:
        await message.answer(texts(lang)["custom_time_invalid"],reply_markup=back_kb(lang))
        return

    data=await state.get_data()
    dt=datetime.fromisoformat(f"{data['date']}T{value}:00").replace(tzinfo=tz_of(u))

    if dt <= datetime.now(tz_of(u)):
        await message.answer(texts(lang)["past"],reply_markup=back_kb(lang))
        return

    await state.update_data(dt=dt.isoformat())
    await state.set_state(Add.repeat)
    await message.answer(texts(lang)["repeat"],reply_markup=repeat_kb(lang))


@dp.callback_query(Add.repeat,F.data=="rep:weekdays")
async def custom_weekdays(c:CallbackQuery,state:FSMContext):
    lang=(await user(c.from_user.id))["language"]; await state.update_data(weekdays=[]); await state.set_state(Add.weekdays)
    await c.message.edit_text(texts(lang)["choose_days"],reply_markup=weekday_kb(lang,set())); await c.answer()


@dp.callback_query(Add.weekdays,F.data.startswith("weekday:"))
async def choose_weekday(c:CallbackQuery,state:FSMContext):
    lang=(await user(c.from_user.id))["language"]; data=await state.get_data(); selected=set(data.get("weekdays",[])); v=c.data.split(":")[1]
    if v=="save":
        if not selected: await c.answer("Select a day",show_alert=True); return
        await state.update_data(repeat="weekly:"+",".join(map(str,sorted(selected)))); await state.set_state(Add.lead)
        await c.message.edit_text(texts(lang)["lead"],reply_markup=lead_kb(lang)); await c.answer(); return
    selected.symmetric_difference_update({int(v)}); await state.update_data(weekdays=list(selected)); await c.message.edit_reply_markup(reply_markup=weekday_kb(lang,selected)); await c.answer()


@dp.callback_query(Add.repeat,F.data.startswith("rep:"))
async def add_rep(c:CallbackQuery,state:FSMContext):
    rep=c.data.split(":")[1]
    if rep=="weekdays": return
    lang=(await user(c.from_user.id))["language"]; await state.update_data(repeat=rep); await state.set_state(Add.lead)
    await c.message.edit_text(texts(lang)["lead"],reply_markup=lead_kb(lang)); await c.answer()


@dp.callback_query(Add.lead,F.data.startswith("lead:"))
async def choose_lead(c:CallbackQuery,state:FSMContext):
    lang=(await user(c.from_user.id))["language"]; data=await state.get_data(); lead=int(c.data.split(":")[1])
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT INTO reminders(telegram_id,title,reminder_at,repeat,category,priority,lead_minutes,status,notified_leads) VALUES(?,?,?,?,?,?,?,?,?)",(c.from_user.id,data["title"],data["dt"],data.get("repeat","once"),data.get("category","other"),data.get("priority","medium"),str(lead),"active",""))
        await db.commit()
    await state.clear()
    await c.message.edit_text(f"<b>{texts(lang)['added']}</b>\n\n📝 {html.escape(data['title'])}\n🎯 {texts(lang)['priority_values'][data.get('priority','medium')]}\n🔔 {texts(lang)['lead_values'][str(lead)]}",reply_markup=main_kb(lang),parse_mode="HTML"); await c.answer()


@dp.callback_query(F.data=="cancel")
async def cancel_cb(c:CallbackQuery,state:FSMContext):
    await state.clear(); lang=(await user(c.from_user.id))["language"]; await home(c.message,lang,True); await c.answer()


@dp.callback_query(F.data=="menu:list")
async def list_cb(c:CallbackQuery):
    u=await user(c.from_user.id); lang=u["language"]; tz=tz_of(u)
    async with aiosqlite.connect(DB) as db:
        q="SELECT DISTINCT r.id,r.title,r.reminder_at,r.repeat,r.category,r.telegram_id FROM reminders r LEFT JOIN shared_members s ON s.reminder_id=r.id WHERE r.status='active' AND (r.telegram_id=? OR s.telegram_id=?) ORDER BY r.reminder_at"
        rows=await (await db.execute(q,(c.from_user.id,c.from_user.id))).fetchall()
    if not rows: await c.message.edit_text(texts(lang)["empty"],reply_markup=back_kb(lang)); await c.answer(); return
    await c.message.edit_text(texts(lang)["list"],reply_markup=back_kb(lang))
    for rid,title,dt,rep,cat,owner in rows:
        e=CAT.get(cat,CAT["other"])[0]; msg=f"{e} <b>{html.escape(title)}</b>\n📅 {datetime.fromisoformat(dt).astimezone(tz):%d.%m.%Y %H:%M}\n🔁 {texts(lang)['repeat_names'].get(rep,rep)}"
        await c.message.answer(msg,reply_markup=list_actions(lang,rid),parse_mode="HTML")
    await c.answer()


@dp.callback_query(F.data.startswith("delete:"))
async def del_cb(c:CallbackQuery):
    rid=int(c.data.split(":")[1]); lang=(await user(c.from_user.id))["language"]
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("UPDATE reminders SET status='archived' WHERE id=? AND telegram_id=?",(rid,c.from_user.id)); await db.commit()
    await c.answer(texts(lang)["deleted"] if cur.rowcount else texts(lang)["notfound"],show_alert=cur.rowcount==0)


@dp.callback_query(F.data.startswith("edit:"))
async def edit_cb(c:CallbackQuery,state:FSMContext):
    rid=int(c.data.split(":")[1]); lang=(await user(c.from_user.id))["language"]
    async with aiosqlite.connect(DB) as db:
        row=await (await db.execute("SELECT title FROM reminders WHERE id=? AND telegram_id=?",(rid,c.from_user.id))).fetchone()
    if not row: await c.answer(texts(lang)["notfound"],show_alert=True); return
    await state.update_data(rid=rid); await state.set_state(Edit.title); await c.message.answer(f"{texts(lang)['edit']}\n\n{html.escape(row[0])}\n\n📝 Новое название:",parse_mode="HTML"); await c.answer()


@dp.message(Edit.title)
async def edit_title(m:Message,state:FSMContext):
    lang=(await user(m.from_user.id))["language"]; await state.update_data(new_title=m.text.strip()); await state.set_state(Edit.dt); await m.answer(texts(lang)["dt"],parse_mode="HTML")


@dp.message(Edit.dt)
async def edit_dt(m:Message,state:FSMContext):
    u=await user(m.from_user.id); lang=u["language"]; tz=tz_of(u)
    try: dt=parse_dt(m.text,tz)
    except: await m.answer(texts(lang)["dt"],parse_mode="HTML"); return
    if dt<=datetime.now(tz): await m.answer(texts(lang)["past"]); return
    d=await state.get_data()
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE reminders SET title=?,reminder_at=?,sent_at=NULL WHERE id=? AND telegram_id=?",(d["new_title"],dt.isoformat(),d["rid"],m.from_user.id)); await db.commit()
    await state.clear(); await m.answer(texts(lang)["added"],reply_markup=main_kb(lang))


@dp.callback_query(F.data.startswith("share:"))
async def share_cb(c:CallbackQuery):
    rid=int(c.data.split(":")[1]); lang=(await user(c.from_user.id))["language"]
    async with aiosqlite.connect(DB) as db:
        row=await (await db.execute("SELECT share_token FROM reminders WHERE id=? AND telegram_id=?",(rid,c.from_user.id))).fetchone()
        if not row: await c.answer(texts(lang)["notfound"],show_alert=True); return
        token=row[0] or os.urandom(8).hex(); await db.execute("UPDATE reminders SET share_token=? WHERE id=?",(token,rid)); await db.commit()
    me=await c.bot.get_me(); await c.message.answer(f"🔗 <code>https://t.me/{me.username}?start=share_{token}</code>",parse_mode="HTML"); await c.answer()


@dp.callback_query(F.data=="menu:today")
async def today_cb(c:CallbackQuery):
    u=await user(c.from_user.id); lang=u["language"]; tz=tz_of(u); today=datetime.now(tz).date().isoformat()
    async with aiosqlite.connect(DB) as db:
        q="SELECT DISTINCT r.title,r.reminder_at,r.category FROM reminders r LEFT JOIN shared_members s ON s.reminder_id=r.id WHERE (r.telegram_id=? OR s.telegram_id=?) AND r.sent_at IS NULL AND r.reminder_at LIKE ? ORDER BY r.reminder_at"
        rows=await (await db.execute(q,(c.from_user.id,c.from_user.id,today+"%"))).fetchall()
    if not rows: text=texts(lang)["nothing"]
    else: text="\n\n".join(f"{CAT.get(cat,CAT['other'])[0]} {html.escape(title)} · {datetime.fromisoformat(dt).astimezone(tz):%H:%M}" for title,dt,cat in rows)
    await c.message.edit_text(text,reply_markup=back_kb(lang),parse_mode="HTML"); await c.answer()


@dp.callback_query(F.data=="menu:lang")
async def lang_menu(c:CallbackQuery):
    await c.message.edit_text(texts((await user(c.from_user.id))["language"])["lang"],reply_markup=lang_kb()); await c.answer()


@dp.callback_query(F.data=="menu:help")
async def help_cb(c:CallbackQuery):
    lang=(await user(c.from_user.id))["language"]; await c.message.edit_text(texts(lang)["help_text"],reply_markup=back_kb(lang)); await c.answer()


@dp.callback_query(F.data=="menu:settings")
async def settings_cb(c:CallbackQuery):
    u=await user(c.from_user.id); lang=u["language"]; await c.message.edit_text(f"<b>{texts(lang)['settings']}</b>\n\n{texts(lang)['tz']}: {u['timezone']}\n{texts(lang)['digest']}: {'✅' if u['digest_enabled'] else '❌'}",reply_markup=settings_kb(lang,bool(u["digest_enabled"])),parse_mode="HTML"); await c.answer()


@dp.callback_query(F.data=="settings:tz")
async def settings_tz(c:CallbackQuery):
    lang=(await user(c.from_user.id))["language"]; await c.message.edit_text(texts(lang)["choose_tz"],reply_markup=tz_kb(lang)); await c.answer()


@dp.callback_query(F.data.startswith("tz:"))
async def tz_cb(c:CallbackQuery):
    key=c.data.split(":")[1]; lang=(await user(c.from_user.id))["language"]; tz=TZS[key][1]
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET timezone=? WHERE telegram_id=?",(tz,c.from_user.id)); await db.commit()
    await c.answer(texts(lang)["tz_saved"]); await settings_cb(c)


@dp.callback_query(F.data=="settings:digest")
async def digest_cb(c:CallbackQuery):
    lang=(await user(c.from_user.id))["language"]
    async with aiosqlite.connect(DB) as db:
        cur=await (await db.execute("SELECT digest_enabled FROM users WHERE telegram_id=?",(c.from_user.id,))).fetchone()
        new=0 if cur and cur[0] else 1
        await db.execute("UPDATE users SET digest_enabled=? WHERE telegram_id=?",(new,c.from_user.id)); await db.commit()
    await c.answer(texts(lang)["digest_on"] if new else texts(lang)["digest_off"]); await settings_cb(c)


@dp.callback_query(F.data=="menu:export")
async def export_cb(c:CallbackQuery):
    path=await export_ics(c.from_user.id); await c.message.answer_document(FSInputFile(path,filename="reminders.ics")); await c.answer()


@dp.callback_query(F.data=="menu:smart")
async def smart_cb(c:CallbackQuery,state:FSMContext):
    lang=(await user(c.from_user.id))["language"]; await state.set_state(Smart.text); await c.message.edit_text(texts(lang)["smart_prompt"],reply_markup=back_kb(lang),parse_mode="HTML"); await c.answer()


@dp.message(Smart.text)
async def smart_msg(m:Message,state:FSMContext):
    u=await user(m.from_user.id); tz=tz_of(u)
    try: parsed,used_ai=await ai_parse(m.text,tz,u["language"])
    except: parsed,used_ai=parse_smart(m.text,tz),False
    if not parsed: await m.answer(texts(u["language"])["smart_prompt"],parse_mode="HTML"); return
    if len(parsed)==2: dt,title=parsed; rep="once"; cat="other"
    else: dt,title,rep,cat=parsed
    if dt<=datetime.now(tz): await m.answer(texts(u["language"])["past"]); return
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT INTO reminders(telegram_id,title,reminder_at,repeat,category) VALUES(?,?,?,?,?)",(m.from_user.id,title,dt.isoformat(),rep,cat)); await db.commit()
    await state.clear(); await m.answer(f"<b>{texts(u['language'])['added']}</b>\n\n📝 {html.escape(title)}\n📅 {dt:%d.%m.%Y %H:%M}\n🔁 {texts(u['language'])['repeat_names'].get(rep,rep)}",reply_markup=main_kb(u["language"]),parse_mode="HTML")


@dp.callback_query(F.data.startswith("snooze:"))
async def snooze(c:CallbackQuery):
    _,mins,rid=c.data.split(":"); mins=int(mins); rid=int(rid); u=await user(c.from_user.id)
    async with aiosqlite.connect(DB) as db:
        row=await (await db.execute("SELECT title,category FROM reminders WHERE id=?",(rid,))).fetchone()
        if not row: await c.answer(texts(u["language"])["notfound"],show_alert=True); return
        dt=datetime.now(tz_of(u))+timedelta(minutes=mins)
        await db.execute("INSERT INTO reminders(telegram_id,title,reminder_at,repeat,category,priority,lead_minutes,status,notified_leads) VALUES(?,?,?,?,?,?,?,?,?)",(c.from_user.id,row[0],dt.isoformat(),"once",row[1],"medium","0","active","")); await db.commit()
    await c.message.edit_reply_markup(reply_markup=None); await c.answer("✅")


@dp.callback_query(F.data.startswith("done:"))
async def done(c:CallbackQuery):
    _,rid=c.data.split(":"); u=await user(c.from_user.id)
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE reminders SET status='completed',sent_at=? WHERE id=? AND repeat='once'",(datetime.now(timezone.utc).isoformat(),int(rid))); await db.commit()
    await c.message.edit_reply_markup(reply_markup=None); await c.answer(texts(u["language"])["done"])


async def share_join(token,uid):
    async with aiosqlite.connect(DB) as db:
        row=await (await db.execute("SELECT id FROM reminders WHERE share_token=?",(token,))).fetchone()
        if not row: return False
        await db.execute("INSERT OR IGNORE INTO shared_members(reminder_id,telegram_id,joined_at) VALUES(?,?,?)",(row[0],uid,datetime.now(timezone.utc).isoformat())); await db.commit()
    return True


async def digest(bot):
    async with aiosqlite.connect(DB) as db:
        users=await (await db.execute("SELECT telegram_id,language,timezone,digest_enabled,last_digest_date FROM users WHERE digest_enabled=1")).fetchall()
    for uid,lang,tzname,on,last in users:
        try: tz=ZoneInfo(tzname)
        except: tz=ZoneInfo(DEFAULT_TZ)
        n=datetime.now(tz)
        if n.hour!=9 or n.minute!=0 or last==n.date().isoformat(): continue
        today=n.date().isoformat()
        async with aiosqlite.connect(DB) as db:
            q="SELECT DISTINCT r.title,r.reminder_at,r.category FROM reminders r LEFT JOIN shared_members s ON s.reminder_id=r.id WHERE (r.telegram_id=? OR s.telegram_id=?) AND r.sent_at IS NULL AND r.reminder_at LIKE ? ORDER BY r.reminder_at"
            rows=await (await db.execute(q,(uid,uid,today+"%"))).fetchall()
            await db.execute("UPDATE users SET last_digest_date=? WHERE telegram_id=?",(today,uid)); await db.commit()
        text=texts(lang)["digest_title"]+"\n\n"+(texts(lang)["empty"] if not rows else "\n".join(f"{CAT.get(cat,CAT['other'])[0]} {datetime.fromisoformat(dt).astimezone(tz):%H:%M} · {html.escape(title)}" for title,dt,cat in rows))
        await bot.send_message(uid,text,parse_mode="HTML",reply_markup=main_kb(lang))


async def worker(bot):
    while True:
        await digest(bot)
        now=datetime.now(timezone.utc)
        async with aiosqlite.connect(DB) as db:
            rows=await (await db.execute("SELECT id,telegram_id,title,reminder_at,repeat,category,lead_minutes,notified_leads FROM reminders WHERE status='active' ORDER BY reminder_at")).fetchall()
            for rid,owner,title,dt_text,rep,cat,lead_text,notified in rows:
                dt=datetime.fromisoformat(dt_text)
                if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
                for lead in [int(x) for x in (lead_text or "0").split(",") if x.strip().isdigit()]:
                    if now < dt-timedelta(minutes=lead) or f",{lead}," in f",{notified},":
                        continue
                    for uid in await recipients(rid,owner):
                        u=await user(uid); local=dt.astimezone(tz_of(u))
                        await bot.send_message(uid,f"<b>{texts(u['language'])['reminder']}</b>\n\n{CAT.get(cat,CAT['other'])[0]} {html.escape(title)}\n⏰ {local:%d.%m.%Y %H:%M}",parse_mode="HTML",reply_markup=action_kb(u["language"],rid))
                    updated=(notified+","+str(lead)).strip(",")
                    await d@dp.callback_query(F.data=="noop")
async def noop(c:CallbackQuery):
    await c.answer()

@dp.callback_query(F.data=="menu:search")
async def menu_search(c:CallbackQuery,state:FSMContext):
    lang=(await user(c.from_user.id))["language"]; await state.set_state(Search.text)
    await c.message.edit_text(texts(lang)["search"],reply_markup=back_kb(lang)); await c.answer()


@dp.message(Search.text)
async def search_text(m:Message,state:FSMContext):
    u=await user(m.from_user.id); lang=u["language"]
    async with aiosqlite.connect(DB) as db:
        rows=await (await db.execute("SELECT id,title,reminder_at,status,category FROM reminders WHERE telegram_id=? AND lower(title) LIKE ? ORDER BY reminder_at DESC LIMIT 30",(m.from_user.id,f"%{m.text.lower()}%"))).fetchall()
    await state.clear()
    if not rows:
        await m.answer(texts(lang)["empty"],reply_markup=back_kb(lang)); return
    for rid,title,dt,status,cat in rows:
        await m.answer(f"#{rid} {CAT.get(cat,CAT['other'])[0]} <b>{html.escape(title)}</b>\n{status} · {datetime.fromisoformat(dt).astimezone(tz_of(u)):%d.%m.%Y %H:%M}",reply_markup=list_actions(lang,rid),parse_mode="HTML")


@dp.callback_query(F.data=="menu:done")
async def menu_done(c:CallbackQuery):
    lang=(await user(c.from_user.id))["language"]
    async with aiosqlite.connect(DB) as db:
        rows=await (await db.execute("SELECT id,title FROM reminders WHERE telegram_id=? AND status='completed' ORDER BY id DESC",(c.from_user.id,))).fetchall()
    text=texts(lang)["completed"] if rows else texts(lang)["empty"]
    if rows: text+="\n\n"+"\n".join(f"✅ #{rid} · {html.escape(title)}" for rid,title in rows)
    await c.message.edit_text(text,reply_markup=back_kb(lang),parse_mode="HTML"); await c.answer()


@dp.callback_query(F.data=="menu:archive")
async def menu_archive(c:CallbackQuery):
    lang=(await user(c.from_user.id))["language"]
    async with aiosqlite.connect(DB) as db:
        rows=await (await db.execute("SELECT id,title FROM reminders WHERE telegram_id=? AND status='archived' ORDER BY id DESC",(c.from_user.id,))).fetchall()
    text=texts(lang)["archived"] if rows else texts(lang)["empty"]
    if rows: text+="\n\n"+"\n".join(f"🗄 #{rid} · {html.escape(title)}" for rid,title in rows)
    await c.message.edit_text(text,reply_markup=back_kb(lang),parse_mode="HTML"); await c.answer()


@dp.callback_query(F.data=="menu:stats")
async def menu_stats(c:CallbackQuery):
    lang=(await user(c.from_user.id))["language"]
    async with aiosqlite.connect(DB) as db:
        active=await (await db.execute("SELECT COUNT(*) FROM reminders WHERE telegram_id=? AND status='active'",(c.from_user.id,))).fetchone()
        completed=await (await db.execute("SELECT COUNT(*) FROM reminders WHERE telegram_id=? AND status='completed'",(c.from_user.id,))).fetchone()
        archived=await (await db.execute("SELECT COUNT(*) FROM reminders WHERE telegram_id=? AND status='archived'",(c.from_user.id,))).fetchone()
    await c.message.edit_text(f"<b>{texts(lang)['stats_title']}</b>\n\n⏰ {active[0]}\n✅ {completed[0]}\n🗄 {archived[0]}",reply_markup=back_kb(lang),parse_mode="HTML"); await c.answer()


@dp.callback_query(F.data=="menu:profile")
async def menu_profile(c:CallbackQuery):
    u=await user(c.from_user.id); lang=u["language"]
    async with aiosqlite.connect(DB) as db: total=await (await db.execute("SELECT COUNT(*) FROM reminders WHERE telegram_id=?",(c.from_user.id,))).fetchone()
    await c.message.edit_text(f"<b>{texts(lang)['profile_title']}</b>\n\n🌐 {lang}\n🌍 {u['timezone']}\n📅 {total[0]}",reply_markup=back_kb(lang),parse_mode="HTML"); await c.answer()


async def worker(bot):
    while True:
        await digest(bot)
        now = datetime.now(timezone.utc)

        async with aiosqlite.connect(DB) as db:
            rows = await (
                await db.execute(
                    "SELECT id,telegram_id,title,reminder_at,repeat,category,lead_minutes,notified_leads "
                    "FROM reminders WHERE status='active' ORDER BY reminder_at"
                )
            ).fetchall()

            for rid, owner, title, dt_text, repeat, category, lead_text, notified in rows:
                dt = datetime.fromisoformat(dt_text)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)

                leads = [
                    int(x)
                    for x in (lead_text or "0").split(",")
                    if x.strip().isdigit()
                ]

                for lead in leads:
                    if now < dt - timedelta(minutes=lead):
                        continue
                    if f",{lead}," in f",{notified},":
                        continue

                    for uid in await recipients(rid, owner):
                        u = await user(uid)
                        local = dt.astimezone(tz_of(u))
                        await bot.send_message(
                            uid,
                            f"<b>{texts(u['language'])['reminder']}</b>\n\n"
                            f"{CAT.get(category, CAT['other'])[0]} {html.escape(title)}\n"
                            f"⏰ {local:%d.%m.%Y %H:%M}",
                            parse_mode="HTML",
                            reply_markup=action_kb(u["language"], rid),
                        )

                    updated = (notified + "," + str(lead)).strip(",")
                    await db.execute(
                        "UPDATE reminders SET notified_leads=? WHERE id=?",
                        (updated, rid),
                    )

                    if lead == 0:
                        nxt = next_dt(dt, repeat)

                        if nxt is None:
                            await db.execute(
                                "UPDATE reminders SET status='completed', sent_at=? WHERE id=?",
                                (datetime.now(timezone.utc).isoformat(), rid),
                            )
                        else:
                            await db.execute(
                                "UPDATE reminders SET reminder_at=?, notified_leads='' WHERE id=?",
                                (nxt.isoformat(), rid),
                            )
                        break

            await db.commit()

        await asyncio.sleep(CHECK)


async def main():
    token=os.getenv("BOT_TOKEN")
    if not token: raise RuntimeError("BOT_TOKEN is not set")
    await db_init()
    async with Bot(token=token) as bot:
        await bot.delete_webhook(drop_pending_updates=False)
        me=await bot.get_me(); print(f"Bot started: @{me.username}",flush=True)
        await asyncio.gather(dp.start_polling(bot),worker(bot))


if __name__=="__main__":
    asyncio.run(main())
