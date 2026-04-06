import os
import psycopg2
from dotenv import load_dotenv

# Load env vars locally (Render uses its own env vars)
load_dotenv()

def get_db_connection():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise Exception("DATABASE_URL is not set")

    conn = psycopg2.connect(
        database_url,
        sslmode="require",
        connect_timeout=10
    )

    return conn
