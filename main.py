from bot.telegram_bot import run_bot
from bot.telegram_bot import user_sessions
from bot.scheduler import setup_scheduler

setup_scheduler(user_sessions)

if __name__ == "__main__":
    print("🚀 Booting up Webhook System for Render...")
    run_bot()