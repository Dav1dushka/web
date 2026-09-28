# Telegram Reminder Bot

A Telegram reminder bot I'm using to learn backend development, async Python and APIs.

### Current features

- calendar-style date picker
- quick time buttons
- reminders in advance
- snooze notifications
- search
- completed history and archive
- priorities and categories
- profile and statistics
- time zones and morning digest
- repeating reminders and custom weekdays
- shared reminders
- smart input with optional OpenAI support
- calendar export
- Russian, English, Italian and Ukrainian UI

### Backend direction

The current Telegram demo still uses SQLite because it is easy to test in GitHub Actions.

The v2 folder adds the PostgreSQL + Redis + FastAPI architecture. PostgreSQL stores reminders, Redis is used for background jobs, and FastAPI exposes the admin API.

Docker Compose is included for local development.

### Stack

Python · aiogram · SQLite · PostgreSQL · Redis · FastAPI · Docker · GitHub Actions
