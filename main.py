import asyncio
from database.models import create_tables
from bot.telegram_bot import run_bot
from bot.scheduler import setup_scheduler

if __name__ == "__main__":
    print("Setting up database...")
    create_tables()

    print("Setting up scheduler...")
    setup_scheduler()

    print("Starting bot...")
    run_bot()