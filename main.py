import threading
import http.server
import socketserver
import os
import time
import asyncio
from bot.telegram_bot import run_bot
from telegram.error import Conflict

def run_fake_port_listener():
    """Spins up a tiny server to satisfy Render's Free Web Service port check."""
    PORT = int(os.getenv("PORT", 10000))
    Handler = http.server.SimpleHTTPRequestHandler
    Handler.log_message = lambda *args: None  

    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"⚓ Free-tier port listener active on port {PORT}")
        httpd.serve_forever()

def start_bot_safely():
    """Tries to boot the bot, waiting out any conflict locks from old deployments."""
    print("🚀 Booting up Telegram Bot Handler...")
    while True:
        try:
            run_bot()
            break 
        except Conflict:
            print("⏳ Telegram Token Conflict detected (Old instance still active). Retrying in 10 seconds...")
            time.sleep(10)
        except Exception as e:
            print(f"❌ Unexpected Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
   
    port_thread = threading.Thread(target=run_fake_port_listener, daemon=True)
    port_thread.start()

    start_bot_safely()