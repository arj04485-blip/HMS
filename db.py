import sqlite3

def get_connection():
    return sqlite3.connect("hostel.db", check_same_thread=False)

def create_tables():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS tenants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        building TEXT,
        floor INTEGER,
        room_type TEXT,
        room_number INTEGER,
        rent INTEGER
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id INTEGER,
        month TEXT,
        paid INTEGER
    )
    """)

    conn.commit()
    conn.close()

create_tables()

