import asyncio

from aiogram import Bot

from app.bot_app import build_dispatcher, home
from app.config import get_settings
from app.db import init_db


async def main():
    settings = get_settings()
    await init_db()

    dp = build_dispatcher()

    async with Bot(token=settings.bot_token) as bot:
        await bot.delete_webhook(drop_pending_updates=False)
        me = await bot.get_me()
        print(f"Reminder Bot V2 started: @{me.username}", flush=True)
        await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
