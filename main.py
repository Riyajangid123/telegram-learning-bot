import threading
import os

from database.models import create_tables
from bot.telegram_bot import run_bot
from bot.scheduler import setup_scheduler
from app import app

if __name__ == "__main__":
    print("Setting up database...")
    create_tables()

    print("Setting up scheduler...")
    setup_scheduler()

    print("Starting bot...")
    threading.Thread(target=run_bot, daemon=True).start()

    print("Starting web server...")
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )