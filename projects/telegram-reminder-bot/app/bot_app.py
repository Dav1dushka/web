import calendar
import html
import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

from aiogram import Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select, or_, update as sql_update, func

from .config import get_settings
from .db import Session, User, Reminder, SharedMember, ensure_user, stats
from .i18n import LANGS, TEXT, CAT, TZS
from .recurrence import next_occurrence

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None


class Add(StatesGroup):
    title = State()
    category = State()
    priority = State()
    date = State()
    time = State()
    repeat = State()
    lead = State()
    weekdays = State()


class Search(StatesGroup):
    query = State()


class Smart(StatesGroup):
    text = State()


WEEKDAYS = {
    0: ("Mon", "Пн", "Пн"),
    1: ("Tue", "Вт", "Вт"),
    2: ("Wed", "Ср", "Ср"),
    3: ("Thu", "Чт", "Чт"),
    4: ("Fri", "Пт", "Пт"),
    5: ("Sat", "Сб", "Сб"),
    6: ("Sun", "Вс", "Нд"),
}


def t(lang: str):
    return TEXT.get(lang, TEXT["en"])


def lang_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
         InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en")],
        [InlineKeyboardButton(text="🇮🇹 Italiano", callback_data="lang:it"),
         InlineKeyboardButton(text="🇺🇦 Українська", callback_data="lang:uk")],
    ])


def back_kb(lang: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang)["back"], callback_data="menu:home")]
    ])


def main_kb(lang: str):
    x = t(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=x["add"], callback_data="menu:add")],
        [InlineKeyboardButton(text=x["list"], callback_data="menu:list"),
         InlineKeyboardButton(text=x["today"], callback_data="menu:today")],
        [InlineKeyboardButton(text=x["search"], callback_data="menu:search"),
         InlineKeyboardButton(text=x["smart"], callback_data="menu:smart")],
        [InlineKeyboardButton(text=x["done_list"], callback_data="menu:done"),
         InlineKeyboardButton(text=x["archive"], callback_data="menu:archive")],
        [InlineKeyboardButton(text=x["stats"], callback_data="menu:stats"),
         InlineKeyboardButton(text=x["profile"], callback_data="menu:profile")],
        [InlineKeyboardButton(text=x["settings"], callback_data="menu:settings"),
         InlineKeyboardButton(text=x["export"], callback_data="menu:export")],
        [InlineKeyboardButton(text=x["lang"], callback_data="menu:lang"),
         InlineKeyboardButton(text=x["help"], callback_data="menu:help")],
    ])


def category_kb(lang: str):
    rows, row = [], []
    for key, (emoji, labels) in CAT.items():
        row.append(InlineKeyboardButton(text=f"{emoji} {labels[lang]}", callback_data=f"cat:{key}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text=t(lang)["cancel"], callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def priority_kb(lang: str):
    p = t(lang)["priority_values"]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=p["high"], callback_data="priority:high")],
        [InlineKeyboardButton(text=p["medium"], callback_data="priority:medium")],
        [InlineKeyboardButton(text=p["low"], callback_data="priority:low")],
        [InlineKeyboardButton(text=t(lang)["cancel"], callback_data="cancel")],
    ])


def repeat_kb(lang: str):
    x = t(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=x["once"], callback_data="repeat:once"),
         InlineKeyboardButton(text=x["daily"], callback_data="repeat:daily")],
        [InlineKeyboardButton(text=x["2d"], callback_data="repeat:2d"),
         InlineKeyboardButton(text=x["week"], callback_data="repeat:week")],
        [InlineKeyboardButton(text=x["month"], callback_data="repeat:month"),
         InlineKeyboardButton(text=x["year"], callback_data="repeat:year")],
        [InlineKeyboardButton(text=x["weekdays"], callback_data="repeat:weekdays")],
        [InlineKeyboardButton(text=x["cancel"], callback_data="cancel")],
    ])


def lead_kb(lang: str):
    x = t(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=x["lead_values"]["0"], callback_data="lead:0")],
        [InlineKeyboardButton(text=x["lead_values"]["10"], callback_data="lead:10"),
         InlineKeyboardButton(text=x["lead_values"]["60"], callback_data="lead:60")],
        [InlineKeyboardButton(text=x["lead_values"]["1440"], callback_data="lead:1440"),
         InlineKeyboardButton(text=x["lead_values"]["10080"], callback_data="lead:10080")],
    ])


def calendar_kb(lang: str, year: int, month: int):
    x = t(lang)
    weeks = calendar.monthcalendar(year, month)
    buttons = [[
        InlineKeyboardButton(text="‹", callback_data=f"cal:nav:{year:04d}-{month:02d}:prev"),
        InlineKeyboardButton(text=f"{year}-{month:02d}", callback_data="noop"),
        InlineKeyboardButton(text="›", callback_data=f"cal:nav:{year:04d}-{month:02d}:next"),
    ]]
    for week in weeks:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="noop"))
            else:
                row.append(InlineKeyboardButton(text=str(day), callback_data=f"cal:day:{year:04d}-{month:02d}-{day:02d}"))
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text=x["cancel"], callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def time_kb(lang: str):
    times = ["08:00", "09:00", "12:00", "18:00", "21:00"]
    rows = []
    for i in range(0, len(times), 2):
        rows.append([InlineKeyboardButton(text=times[i], callback_data=f"time:{times[i]}"),
                     InlineKeyboardButton(text=times[i + 1], callback_data=f"time:{times[i + 1]}")])
    rows.append([InlineKeyboardButton(text="10:30", callback_data="time:10:30"),
                 InlineKeyboardButton(text="20:30", callback_data="time:20:30")])
    rows.append([InlineKeyboardButton(text=lang == "ru" and "✏️ Другое" or "✏️ Custom", callback_data="time:custom")])
    rows.append([InlineKeyboardButton(text=t(lang)["back"], callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def weekday_kb(lang: str, selected: set[int]):
    rows = []
    row = []
    labels = [WEEKDAYS[i][1 if lang == "ru" else 0] for i in range(7)]
    for i in range(7):
        mark = "✅ " if i in selected else ""
        row.append(InlineKeyboardButton(text=f"{mark}{labels[i]}", callback_data=f"weekday:{i}"))
        if len(row) == 2:
            rows.append(row); row=[]
    if row: rows.append(row)
    rows.append([InlineKeyboardButton(text=t(lang)["saved"], callback_data="weekday:save")])
    rows.append([InlineKeyboardButton(text=t(lang)["cancel"], callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def reminder_actions(lang: str, rid: int):
    x = t(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=x["snooze10"], callback_data=f"snooze:10:{rid}"),
         InlineKeyboardButton(text=x["snooze60"], callback_data=f"snooze:60:{rid}")],
        [InlineKeyboardButton(text=x["snooze1440"], callback_data=f"snooze:1440:{rid}"),
         InlineKeyboardButton(text=x["done"], callback_data=f"done:{rid}")],
    ])


def item_kb(lang: str, rid: int):
    x = t(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{x['edit']} #{rid}", callback_data=f"edit:{rid}"),
         InlineKeyboardButton(text=f"{x['delete']} #{rid}", callback_data=f"delete:{rid}")],
        [InlineKeyboardButton(text=f"{x['share']} #{rid}", callback_data=f"share:{rid}")],
    ])


def settings_kb(lang: str, digest: bool):
    x=t(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=x["tz"], callback_data="settings:tz")],
        [InlineKeyboardButton(text=f"{x['digest']} {'✅' if digest else '❌'}", callback_data="settings:digest")],
        [InlineKeyboardButton(text=x["back"], callback_data="menu:home")],
    ])


def tz_kb(lang: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=name, callback_data=f"tz:{key}")]
        for key, (name, _) in TZS.items()
    ] + [[InlineKeyboardButton(text=t(lang)["back"], callback_data="menu:settings")]])


def parse_user_dt(value: str, tz: ZoneInfo):
    return datetime.strptime(value.strip(), "%d.%m.%Y %H:%M").replace(tzinfo=tz)


def next_local_smart(text: str, tz: ZoneInfo):
    now = datetime.now(tz)
    m_time = re.search(r"(?:в|о|at|alle)\s*(\d{1,2})(?::(\d{2}))?", text, re.I)
    hour = int(m_time.group(1)) if m_time else 9
    minute = int(m_time.group(2) or 0) if m_time else 0
    patterns = [
        (r"(?:через|in|tra)\s+(\d+)\s*(?:дн\w*|day\w*|giorn\w*|дн\w*)", "day"),
        (r"(?:через|in|tra)\s+(\d+)\s*(?:нед\w*|week\w*|settim\w*|тиж\w*)", "week"),
        (r"(?:через|in|tra)\s+(\d+)\s*(?:месяц\w*|month\w*|mes\w*|місяц\w*)", "month"),
        (r"(?:через|in|tra)\s+(\d+)\s*(?:год\w*|year\w*|ann\w*|рок\w*)", "year"),
    ]
    for pattern, unit in patterns:
        m=re.search(pattern, text, re.I)
        if not m: continue
        n=int(m.group(1))
        title=re.sub(pattern, "", text, flags=re.I).strip(" ,")
        if unit == "day": dt=now+timedelta(days=n)
        elif unit=="week": dt=now+timedelta(days=7*n)
        elif unit=="month":
            month=now.month-1+n; year=now.year+month//12; month=month%12+1
            dt=now.replace(year=year,month=month,day=min(now.day,calendar.monthrange(year,month)[1]))
        else:
            dt=now.replace(year=now.year+n,day=28 if now.month==2 and now.day==29 else now.day)
        return dt.replace(hour=hour,minute=minute,second=0,microsecond=0), title or text
    return None


async def ai_parse(text: str, tz: ZoneInfo, lang: str):
    local=next_local_smart(text,tz)
    settings=get_settings()
    if not settings.openai_api_key or AsyncOpenAI is None:
        return local
    try:
        client=AsyncOpenAI(api_key=settings.openai_api_key)
        prompt=("Return JSON with title, datetime and repeat. repeat=once,daily,2d,week,month,year. "
                f"Current local time={datetime.now(tz):%Y-%m-%d %H:%M}; timezone={tz.key}; text={text}")
        response=await client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role":"system","content":"Extract a reminder."},{"role":"user","content":prompt}],
            temperature=0,
            response_format={"type":"json_object"},
        )
        data=json.loads(response.choices[0].message.content)
        dt=datetime.fromisoformat(data["datetime"]).replace(tzinfo=tz)
        return dt,data["title"],data.get("repeat","once")
    except Exception:
        return local


def build_dispatcher():
    dp=Dispatcher()

    @dp.message(Command("start"))
    async def start(message: Message, state: FSMContext):
        await state.clear()
        async with Session() as session:
            user=await ensure_user(session,message.from_user.id)
            if user.created_at:
                lang=user.language
        if not user.language:
            await message.answer("Choose your language / Выберите язык / Scegli la lingua / Оберіть мову:",reply_markup=lang_keyboard())
            return
        await home(message,user.language)

    @dp.callback_query(F.data.startswith("lang:"))
    async def select_lang(c: CallbackQuery):
        lang=c.data.split(":")[1]
        async with Session() as session:
            user=await ensure_user(session,c.from_user.id)
            user.language=lang
            await session.commit()
        await c.message.edit_text(t(lang)["welcome"],parse_mode="HTML")
        await home(c.message,lang)
        await c.answer()

    @dp.callback_query(F.data=="menu:home")
    async def menu_home(c: CallbackQuery,state:FSMContext):
        await state.clear()
        async with Session() as session: user=await ensure_user(session,c.from_user.id)
        await home(c.message,user.language,True)
        await c.answer()

    @dp.callback_query(F.data=="menu:add")
    async def add_start(c:CallbackQuery,state:FSMContext):
        async with Session() as session: user=await ensure_user(session,c.from_user.id)
        await state.set_state(Add.title)
        await c.message.edit_text(t(user.language)["title"],reply_markup=back_kb(user.language))
        await c.answer()

    @dp.message(Add.title)
    async def add_title(message:Message,state:FSMContext):
        async with Session() as session: user=await ensure_user(session,message.from_user.id)
        await state.update_data(title=message.text.strip())
        await state.set_state(Add.category)
        await message.answer(t(user.language)["cat"],reply_markup=category_kb(user.language))

    @dp.callback_query(Add.category,F.data.startswith("cat:"))
    async def add_category(c:CallbackQuery,state:FSMContext):
        async with Session() as session: user=await ensure_user(session,c.from_user.id)
        await state.update_data(category=c.data.split(":")[1])
        await state.set_state(Add.priority)
        await c.message.edit_text(t(user.language)["priority"],reply_markup=priority_kb(user.language))
        await c.answer()

    @dp.callback_query(Add.priority,F.data.startswith("priority:"))
    async def add_priority(c:CallbackQuery,state:FSMContext):
        async with Session() as session: user=await ensure_user(session,c.from_user.id)
        await state.update_data(priority=c.data.split(":")[1])
        await state.set_state(Add.date)
        today=datetime.now(ZoneInfo(user.timezone))
        await c.message.edit_text(t(user.language)["dt"],reply_markup=calendar_kb(user.language,today.year,today.month))
        await c.answer()

    @dp.callback_query(Add.date,F.data.startswith("cal:nav:"))
    async def cal_nav(c:CallbackQuery,state:FSMContext):
        _,_,ym,direction=c.data.split(":")
        y,m=map(int,ym.split("-"))
        if direction=="prev": m-=1
        else: m+=1
        if m==0: y-=1;m=12
        if m==13: y+=1;m=1
        async with Session() as session:user=await ensure_user(session,c.from_user.id)
        await c.message.edit_reply_markup(reply_markup=calendar_kb(user.language,y,m))
        await c.answer()

    @dp.callback_query(Add.date,F.data.startswith("cal:day:"))
    async def cal_day(c:CallbackQuery,state:FSMContext):
        date_text=c.data.split(":")[2]
        await state.update_data(date=date_text)
        async with Session() as session:user=await ensure_user(session,c.from_user.id)
        await state.set_state(Add.time)
        await c.message.edit_text(t(user.language)["time"],reply_markup=time_kb(user.language))
        await c.answer()

    @dp.callback_query(Add.time,F.data.startswith("time:"))
    async def choose_time(c:CallbackQuery,state:FSMContext):
        value=c.data.split(":",1)[1]
        if value=="custom":
            await c.message.answer("HH:MM")
            await c.answer()
            return
        data=await state.get_data()
        async with Session() as session:user=await ensure_user(session,c.from_user.id)
        dt=datetime.fromisoformat(f"{data['date']}T{value}:00").replace(tzinfo=ZoneInfo(user.timezone))
        if dt <= datetime.now(ZoneInfo(user.timezone)):
            await c.answer("Past time",show_alert=True); return
        await state.update_data(dt=dt.isoformat())
        await state.set_state(Add.repeat)
        await c.message.edit_text(t(user.language)["repeat"],reply_markup=repeat_kb(user.language))
        await c.answer()

    @dp.callback_query(Add.repeat,F.data=="repeat:weekdays")
    async def custom_weekdays(c:CallbackQuery,state:FSMContext):
        async with Session() as session:user=await ensure_user(session,c.from_user.id)
        await state.update_data(weekdays=set())
        await state.set_state(Add.weekdays)
        await c.message.edit_text(t(user.language)["repeat_custom"],reply_markup=weekday_kb(user.language,set()))
        await c.answer()

    @dp.callback_query(Add.weekdays,F.data.startswith("weekday:"))
    async def pick_weekday(c:CallbackQuery,state:FSMContext):
        data=await state.get_data()
        selected=set(data.get("weekdays",set()))
        action=c.data.split(":")[1]
        if action=="save":
            if not selected: await c.answer("Select at least one day",show_alert=True); return
            await state.update_data(repeat="weekly:"+",".join(map(str,sorted(selected))))
            async with Session() as session:user=await ensure_user(session,c.from_user.id)
            await state.set_state(Add.lead)
            await c.message.edit_text(t(user.language)["lead"],reply_markup=lead_kb(user.language))
        else:
            selected.symmetric_difference_update({int(action)})
            await state.update_data(weekdays=selected)
            async with Session() as session:user=await ensure_user(session,c.from_user.id)
            await c.message.edit_reply_markup(reply_markup=weekday_kb(user.language,selected))
        await c.answer()

    @dp.callback_query(Add.repeat,F.data.startswith("repeat:"))
    async def choose_repeat(c:CallbackQuery,state:FSMContext):
        repeat=c.data.split(":")[1]
        if repeat=="weekdays": return
        async with Session() as session:user=await ensure_user(session,c.from_user.id)
        await state.update_data(repeat=repeat)
        await state.set_state(Add.lead)
        await c.message.edit_text(t(user.language)["lead"],reply_markup=lead_kb(user.language))
        await c.answer()

    @dp.callback_query(Add.lead,F.data.startswith("lead:"))
    async def choose_lead(c:CallbackQuery,state:FSMContext):
        data=await state.get_data()
        lead=int(c.data.split(":")[1])
        reminder_at=datetime.fromisoformat(data["dt"])
        async with Session() as session:
            user=await ensure_user(session,c.from_user.id)
            session.add(Reminder(owner_id=c.from_user.id,title=data["title"],category=data.get("category","other"),priority=data.get("priority","medium"),reminder_at=reminder_at.astimezone(timezone.utc),repeat=data.get("repeat","once"),lead_minutes=str(lead)))
            await session.commit()
        await state.clear()
        await c.message.edit_text(f"<b>{t(user.language)['added']}</b>\n\n📝 {html.escape(data['title'])}\n🔁 {t(user.language)['repeat_values'].get(data.get('repeat'),data.get('repeat'))}\n🔔 {t(user.language)['lead_values'].get(str(lead),str(lead))}",reply_markup=main_kb(user.language),parse_mode="HTML")
        await c.answer()

    @dp.callback_query(F.data=="cancel")
    async def cancel(c:CallbackQuery,state:FSMContext):
        await state.clear()
        async with Session() as session:user=await ensure_user(session,c.from_user.id)
        await home(c.message,user.language,True); await c.answer()

    async def list_view(message:Message, mode:str="active"):
        async with Session() as session:
            user=await ensure_user(session,message.from_user.id)
            if mode=="active":
                cond=Reminder.status=="active"
            elif mode=="completed":
                cond=Reminder.status=="completed"
            else:
                cond=Reminder.status=="archived"
            rows=(await session.execute(select(Reminder).where(Reminder.owner_id==message.from_user.id,cond).order_by(Reminder.reminder_at.desc()).limit(50))).scalars().all()
        if not rows:
            await message.answer(t(user.language)["empty"],reply_markup=back_kb(user.language)); return
        await message.answer(t(user.language)["list"] if mode=="active" else mode.title(),reply_markup=back_kb(user.language))
        for r in rows:
            await message.answer(f"{CAT.get(r.category,CAT['other'])[0]} <b>{html.escape(r.title)}</b>\n📅 {r.reminder_at.astimezone(ZoneInfo(user.timezone)):%d.%m.%Y %H:%M}\n🎯 {t(user.language)['priority_values'][r.priority]}",reply_markup=item_kb(user.language,r.id),parse_mode="HTML")

    @dp.callback_query(F.data=="menu:list")
    async def menu_list(c:CallbackQuery):
        await list_view(c.message,"active"); await c.answer()

    @dp.callback_query(F.data=="menu:done")
    async def menu_done(c:CallbackQuery):
        await list_view(c.message,"completed"); await c.answer()

    @dp.callback_query(F.data=="menu:archive")
    async def menu_archive(c:CallbackQuery):
        await list_view(c.message,"archived"); await c.answer()

    @dp.callback_query(F.data=="menu:today")
    async def menu_today(c:CallbackQuery):
        async with Session() as session:
            user=await ensure_user(session,c.from_user.id); tz=ZoneInfo(user.timezone); today=datetime.now(tz).date()
            start=datetime.combine(today,datetime.min.time(),tzinfo=tz).astimezone(timezone.utc)
            end=start+timedelta(days=1)
            rows=(await session.execute(select(Reminder).where(Reminder.owner_id==c.from_user.id,Reminder.status=="active",Reminder.reminder_at>=start,Reminder.reminder_at<end).order_by(Reminder.reminder_at))).scalars().all()
        text=t(user.language)["nothing"] if not rows else "\n".join(f"• {r.reminder_at.astimezone(tz):%H:%M} {html.escape(r.title)}" for r in rows)
        await c.message.edit_text(text,reply_markup=back_kb(user.language),parse_mode="HTML"); await c.answer()

    @dp.callback_query(F.data=="menu:search")
    async def menu_search(c:CallbackQuery,state:FSMContext):
        async with Session() as session:user=await ensure_user(session,c.from_user.id)
        await state.set_state(Search.query); await c.message.edit_text(t(user.language)["search_prompt"],reply_markup=back_kb(user.language)); await c.answer()

    @dp.message(Search.query)
    async def search_query(m:Message,state:FSMContext):
        async with Session() as session:
            user=await ensure_user(session,m.from_user.id)
            term=f"%{m.text.lower()}%"
            rows=(await session.execute(select(Reminder).where(Reminder.owner_id==m.from_user.id,Reminder.title.ilike(term)).order_by(Reminder.reminder_at.desc()).limit(30))).scalars().all()
        await state.clear()
        if not rows: await m.answer(t(user.language)["empty"],reply_markup=back_kb(user.language)); return
        for r in rows:
            await m.answer(f"#{r.id} {html.escape(r.title)}\n{r.status} · {r.reminder_at.astimezone(ZoneInfo(user.timezone)):%d.%m.%Y %H:%M}",reply_markup=item_kb(user.language,r.id),parse_mode="HTML")

    @dp.callback_query(F.data.startswith("delete:"))
    async def delete(c:CallbackQuery):
        rid=int(c.data.split(":")[1])
        async with Session() as session:
            r=await session.get(Reminder,rid)
            user=await ensure_user(session,c.from_user.id)
            if not r or r.owner_id!=c.from_user.id: await c.answer(t(user.language)["notfound"],show_alert=True); return
            r.status="archived"; await session.commit()
        await c.answer(t(user.language)["deleted"])

    @dp.callback_query(F.data.startswith("done:"))
    async def done(c:CallbackQuery):
        rid=int(c.data.split(":")[1])
        async with Session() as session:
            r=await session.get(Reminder,rid); user=await ensure_user(session,c.from_user.id)
            if not r: await c.answer(t(user.language)["notfound"],show_alert=True); return
            if r.repeat=="once": r.status="completed"
            else:
                r.reminder_at=next_occurrence(r.reminder_at,r.repeat)
            await session.commit()
        await c.message.edit_reply_markup(reply_markup=None); await c.answer(t(user.language)["done"])

    @dp.callback_query(F.data.startswith("snooze:"))
    async def snooze(c:CallbackQuery):
        _,minutes,rid=c.data.split(":")
        async with Session() as session:
            r=await session.get(Reminder,int(rid)); user=await ensure_user(session,c.from_user.id)
            if not r: await c.answer(t(user.language)["notfound"],show_alert=True); return
            session.add(Reminder(owner_id=c.from_user.id,title=r.title,category=r.category,priority=r.priority,reminder_at=datetime.now(timezone.utc)+timedelta(minutes=int(minutes)),repeat="once",lead_minutes="0"))
            await session.commit()
        await c.message.edit_reply_markup(reply_markup=None); await c.answer(t(user.language)["saved"])

    @dp.callback_query(F.data.startswith("edit:"))
    async def edit(c:CallbackQuery):
        await c.answer("Editing from the admin panel is available in this version.")

    @dp.callback_query(F.data.startswith("share:"))
    async def share(c:CallbackQuery):
        rid=int(c.data.split(":")[1])
        async with Session() as session:
            r=await session.get(Reminder,rid); user=await ensure_user(session,c.from_user.id)
            if not r or r.owner_id!=c.from_user.id: await c.answer(t(user.language)["notfound"],show_alert=True); return
            if not r.share_token: r.share_token=uuid4().hex
            await session.commit()
        settings=get_settings()
        me=await c.bot.get_me()
        await c.message.answer(f"🔗 <code>https://t.me/{me.username}?start=share_{r.share_token}</code>",parse_mode="HTML")
        await c.answer()

    @dp.callback_query(F.data=="menu:profile")
    async def profile(c:CallbackQuery):
        async with Session() as session:
            user=await ensure_user(session,c.from_user.id); st=await stats(session,c.from_user.id)
        await c.message.edit_text(f"<b>{t(user.language)['profile']}</b>\n\n🌐 {user.language}\n🌍 {user.timezone}\n📅 {st['active']} active\n✅ {st['completed']} completed",reply_markup=back_kb(user.language),parse_mode="HTML"); await c.answer()

    @dp.callback_query(F.data=="menu:stats")
    async def menu_stats(c:CallbackQuery):
        async with Session() as session:user=await ensure_user(session,c.from_user.id); st=await stats(session,c.from_user.id)
        await c.message.edit_text(f"<b>{t(user.language)['stats_title']}</b>\n\n⏰ Active: {st['active']}\n✅ Completed: {st['completed']}\n🗄 Archived: {st['archived']}",reply_markup=back_kb(user.language),parse_mode="HTML"); await c.answer()

    @dp.callback_query(F.data=="menu:settings")
    async def menu_settings(c:CallbackQuery):
        async with Session() as session:user=await ensure_user(session,c.from_user.id)
        await c.message.edit_text(f"<b>{t(user.language)['settings']}</b>\n\n🌍 {user.timezone}\n🌅 {t(user.language)['digest']} {'✅' if user.digest_enabled else '❌'}",reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t(user.language)["tz"],callback_data="settings:tz")],
            [InlineKeyboardButton(text="🌅 Digest",callback_data="settings:digest")],
            [InlineKeyboardButton(text=t(user.language)["back"],callback_data="menu:home")],
        ]),parse_mode="HTML"); await c.answer()

    @dp.callback_query(F.data=="settings:tz")
    async def settings_tz(c:CallbackQuery):
        async with Session() as session:user=await ensure_user(session,c.from_user.id)
        await c.message.edit_text(t(user.language)["choose_tz"],reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=name,callback_data=f"tz:{key}")] for key,(name,_) in TZS.items()
        ]+[ [InlineKeyboardButton(text=t(user.language)["back"],callback_data="menu:settings")] ])); await c.answer()

    @dp.callback_query(F.data.startswith("tz:"))
    async def tz_select(c:CallbackQuery):
        key=c.data.split(":")[1]
        async with Session() as session:
            user=await ensure_user(session,c.from_user.id); user.timezone=TZS[key][1]; await session.commit()
        await c.answer(t(user.language)["tz_saved"]); await menu_settings(c)

    @dp.callback_query(F.data=="settings:digest")
    async def digest(c:CallbackQuery):
        async with Session() as session:
            user=await ensure_user(session,c.from_user.id); user.digest_enabled=not user.digest_enabled; await session.commit()
        await c.answer(t(user.language)["saved"]); await menu_settings(c)

    @dp.callback_query(F.data=="menu:lang")
    async def menu_lang(c:CallbackQuery):
        async with Session() as session:user=await ensure_user(session,c.from_user.id)
        await c.message.edit_text(t(user.language)["choose_lang"],reply_markup=lang_keyboard()); await c.answer()

    @dp.callback_query(F.data=="menu:help")
    async def help_cb(c:CallbackQuery):
        async with Session() as session:user=await ensure_user(session,c.from_user.id)
        await c.message.edit_text(t(user.language)["help"],reply_markup=back_kb(user.language)); await c.answer()

    @dp.callback_query(F.data=="menu:export")
    async def export(c:CallbackQuery):
        async with Session() as session:
            user=await ensure_user(session,c.from_user.id)
            rows=(await session.execute(select(Reminder).where(Reminder.owner_id==c.from_user.id))).scalars().all()
        path=tempfile.mktemp(suffix=".ics")
        lines=["BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//ReminderBot//EN"]
        for r in rows:
            lines += ["BEGIN:VEVENT",f"UID:{r.id}@reminderbot",f"DTSTAMP:{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}",f"DTSTART:{r.reminder_at:%Y%m%dT%H%M%SZ}",f"SUMMARY:{r.title.replace(',','\\,').replace(';','\\;') }"]
            if r.repeat=="daily": lines.append("RRULE:FREQ=DAILY")
            elif r.repeat=="2d": lines.append("RRULE:FREQ=DAILY;INTERVAL=2")
            elif r.repeat=="week": lines.append("RRULE:FREQ=WEEKLY")
            elif r.repeat=="month": lines.append("RRULE:FREQ=MONTHLY")
            elif r.repeat=="year": lines.append("RRULE:FREQ=YEARLY")
            lines.append("END:VEVENT")
        lines.append("END:VCALENDAR")
        open(path,"w",encoding="utf-8").write("\r\n".join(lines))
        await c.message.answer_document(FSInputFile(path,filename="reminders.ics")); await c.answer()

    @dp.callback_query(F.data=="menu:smart")
    async def smart(c:CallbackQuery,state:FSMContext):
        async with Session() as session:user=await ensure_user(session,c.from_user.id)
        await state.set_state(Smart.text); await c.message.edit_text(t(user.language)["smart_prompt"],reply_markup=back_kb(user.language),parse_mode="HTML"); await c.answer()

    @dp.message(Smart.text)
    async def smart_message(m:Message,state:FSMContext):
        async with Session() as session:user=await ensure_user(session,m.from_user.id)
        tz=ZoneInfo(user.timezone)
        parsed=await ai_parse(m.text,tz,user.language)
        if not parsed: await m.answer(t(user.language)["smart_prompt"],parse_mode="HTML"); return
        if len(parsed)==2: dt,title=parsed; repeat="once"
        else: dt,title,repeat=parsed
        session_user=user
        async with Session() as session:
            session.add(Reminder(owner_id=m.from_user.id,title=title,reminder_at=dt.astimezone(timezone.utc),repeat=repeat))
            await session.commit()
        await state.clear(); await m.answer(f"<b>{t(user.language)['added']}</b>\n\n📝 {html.escape(title)}\n📅 {dt:%d.%m.%Y %H:%M}\n🔁 {t(user.language)['repeat_values'].get(repeat,repeat)}",reply_markup=main_kb(user.language),parse_mode="HTML")

    @dp.message(Command("today"))
    async def today_cmd(m:Message):
        await m.answer("Use the Today button.")

    return dp


async def home(message: Message, language: str, edit: bool=False):
    text=f"{t(language)['welcome']}\n\n<b>{t(language)['menu']}</b>"
    if edit: await message.edit_text(text,reply_markup=main_kb(language),parse_mode="HTML")
    else: await message.answer(text,reply_markup=main_kb(language),parse_mode="HTML")
