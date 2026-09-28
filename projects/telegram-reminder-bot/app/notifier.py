import asyncio
import json
from datetime import datetime, timezone

import redis.asyncio as redis
from aiogram import Bot
from sqlalchemy import select

from .config import get_settings
from .db import Session, Reminder, User, Delivery
from .recurrence import next_occurrence


async def main():
    settings=get_settings()
    r=redis.from_url(settings.redis_url,decode_responses=True)
    bot=Bot(settings.bot_token)
    while True:
        item=await r.blpop("reminder:queue",timeout=5)
        if not item:
            continue
        job=json.loads(item[1])
        async with Session() as session:
            delivery=await session.get(Delivery,(job["reminder_id"],job["occurrence_at"],job["lead_minutes"],job["recipient_id"]))
            reminder=await session.get(Reminder,job["reminder_id"])
            user=await session.get(User,job["recipient_id"])
            if not delivery or delivery.sent_at or not reminder or reminder.status!="active" or not user:
                continue
            title=reminder.title
            await bot.send_message(user.telegram_id,f"🔔 Reminder\n\n{title}")
            delivery.sent_at=datetime.now(timezone.utc)
            if job["lead_minutes"]==0:
                nxt=next_occurrence(reminder.reminder_at,reminder.repeat)
                if nxt:
                    reminder.reminder_at=nxt
                else:
                    reminder.status="completed"
            await session.commit()


if __name__=="__main__":
    asyncio.run(main())
