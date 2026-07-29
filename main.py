from bot.telegram_bot import run_bot
import os


if __name__ == "__main__":
    print("🚀 Starting Telegram Learning Bot...")

    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is missing")

    run_bot()