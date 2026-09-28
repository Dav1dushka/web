import asyncio
import json
from datetime import datetime, timedelta, timezone

import redis.asyncio as redis
from sqlalchemy import select, or_

from .config import get_settings
from .db import Session, Reminder, SharedMember, Delivery, init_db


async def main():
    settings=get_settings()
    await init_db()
    r=redis.from_url(settings.redis_url,decode_responses=True)
    while True:
        now=datetime.now(timezone.utc)
        async with Session() as session:
            reminders=(await session.execute(select(Reminder).where(Reminder.status=="active"))).scalars().all()
            for reminder in reminders:
                leads=[int(x) for x in reminder.lead_minutes.split(",") if x.strip().isdigit()]
                occurrence=reminder.reminder_at
                recipients=[reminder.owner_id]
                members=(await session.execute(select(SharedMember.telegram_id).where(SharedMember.reminder_id==reminder.id))).scalars().all()
                recipients += list(members)
                for lead in leads:
                    target=occurrence-timedelta(minutes=lead)
                    if target <= now:
                        for recipient in set(recipients):
                            key={"reminder_id":reminder.id,"occurrence_at":occurrence.isoformat(),"lead_minutes":lead,"recipient_id":recipient}
                            delivery=await session.get(Delivery,(reminder.id,occurrence,lead,recipient))
                            if not delivery:
                                delivery=Delivery(reminder_id=reminder.id,occurrence_at=occurrence,lead_minutes=lead,recipient_id=recipient)
                                session.add(delivery)
                                await session.flush()
                                await r.rpush("reminder:queue",json.dumps(key))
            await session.commit()
        await asyncio.sleep(5)


if __name__=="__main__":
    asyncio.run(main())
