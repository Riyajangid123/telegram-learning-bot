import os
from dotenv import load_dotenv

print("Current folder:", os.getcwd())

load_dotenv()

print("Env file exists:", os.path.exists(".env"))
print("Token:", os.getenv("TELEGRAM_BOT_TOKEN"))