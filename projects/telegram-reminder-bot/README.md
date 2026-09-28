# Telegram Reminder Bot

A small Telegram bot for reminders.

I made it to practice async Python, SQLite and background jobs.

### Example

```
/add 2026-10-27 09:00 | Mom's birthday | yearly
```

The bot stores the reminder and sends a Telegram message when the time comes.

### Commands

```
/add
/list
/today
/delete
/help
```

### Built with

Python · aiogram · SQLite

The bot supports one-time reminders and yearly reminders.

For now it uses the server's local time. A timezone setting would be a good next step.
