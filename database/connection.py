import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    database_url = os.getenv("DATABASE_URL")
    print(f"DEBUG URL exists: {database_url is not None}")
    conn = psycopg2.connect(database_url, sslmode="require")
    return conn