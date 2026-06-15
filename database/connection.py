import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    conn = psycopg2.connect(
        host=os.getenv("host"),
        user=os.getenv("user"),
        password=os.getenv("password"),
        dbname=os.getenv("database"),
        port=int(os.getenv("port", 5432)),
        sslmode="require"  
    )
    return conn