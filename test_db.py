print("🔥 test_db.py started running...")   # Debug print

from db_config import get_db_connection

print("🚀 Import successful, now testing DB connection...")

def test_connection():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT NOW();")
        result = cur.fetchone()
        print("✅ Connected to Supabase! Current time:", result)
        cur.close()
        conn.close()
    except Exception as e:
        print("❌ Connection failed:", e)

if __name__ == "__main__":
    print("▶ Running test_connection()...")
    test_connection()
