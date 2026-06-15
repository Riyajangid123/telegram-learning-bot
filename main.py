from database.models import create_tables
from bot.telegram_bot import run_bot
from threading import Thread
from server import app as flask_app

def run_server():
    flask_app.run(host="0.0.0.0", port=8080)

def main():
    print("Setting up database...")
    create_tables()
    print("✅ Database ready!")

    Thread(target=run_server, daemon=True).start()
    print("✅ Health check server running!")


    print("Starting bot...")
    run_bot()

if __name__ == "__main__":
    main()