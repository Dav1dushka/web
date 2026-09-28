import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    bot_token: str
    database_url: str
    redis_url: str
    default_timezone: str
    openai_api_key: str | None
    openai_model: str


def get_settings() -> Settings:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN is not set")

    return Settings(
        bot_token=token,
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://reminders:reminders@localhost:5432/reminders",
        ),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        default_timezone=os.getenv("BOT_TIMEZONE", "Europe/Prague"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
    )
