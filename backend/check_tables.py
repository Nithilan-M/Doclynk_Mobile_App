import os
from db_config import get_db_connection

def check_schema():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
    tables = cur.fetchall()
    print("Tables in public schema:")
    for table in tables:
        print(f"- {table[0]}")
        cur.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name='{table[0]}';")
        cols = cur.fetchall()
        for col in cols:
            print(f"  * {col[0]} ({col[1]})")
    cur.close()
    conn.close()

if __name__ == '__main__':
    check_schema()
