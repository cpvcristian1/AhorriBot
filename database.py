import sqlite3
import os
import time

DB_PATH = os.path.join(os.path.dirname(__file__), "deals.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Tabla de chollos ya notificados (evitar duplicados en las últimas 24h)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notified_deals (
            asin TEXT PRIMARY KEY,
            title TEXT,
            new_price REAL,
            old_price REAL,
            drop_pct REAL,
            notified_at INTEGER
        )
    """)
    
    # Tabla de configuración de usuario
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            chat_id TEXT PRIMARY KEY,
            min_drop_pct REAL DEFAULT 30.0,
            min_price REAL DEFAULT 20.0
        )
    """)

    # Tabla de productos específicos seguidos (Watchlist manual)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT,
            asin TEXT,
            product_name TEXT,
            target_price REAL,
            created_at INTEGER,
            UNIQUE(chat_id, asin)
        )
    """)
    
    conn.commit()
    conn.close()

def is_already_notified(asin: str, cooldown_hours: int = 24) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cutoff = int(time.time()) - (cooldown_hours * 3600)
    cursor.execute("SELECT 1 FROM notified_deals WHERE asin = ? AND notified_at > ?", (asin, cutoff))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def mark_as_notified(asin: str, title: str, new_price: float, old_price: float, drop_pct: float):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO notified_deals (asin, title, new_price, old_price, drop_pct, notified_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(asin) DO UPDATE SET
            new_price = excluded.new_price,
            old_price = excluded.old_price,
            drop_pct = excluded.drop_pct,
            notified_at = excluded.notified_at
    """, (asin, title, new_price, old_price, drop_pct, int(time.time())))
    conn.commit()
    conn.close()

def get_user_settings(chat_id: str, default_drop: float = 30.0, default_min_price: float = 20.0):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT min_drop_pct, min_price FROM user_settings WHERE chat_id = ?", (str(chat_id),))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"min_drop_pct": row["min_drop_pct"], "min_price": row["min_price"]}
    return {"min_drop_pct": default_drop, "min_price": default_min_price}

def update_user_setting(chat_id: str, min_drop_pct: float = None, min_price: float = None):
    conn = get_connection()
    cursor = conn.cursor()
    current = get_user_settings(chat_id)
    new_drop = min_drop_pct if min_drop_pct is not None else current["min_drop_pct"]
    new_price = min_price if min_price is not None else current["min_price"]
    
    cursor.execute("""
        INSERT INTO user_settings (chat_id, min_drop_pct, min_price)
        VALUES (?, ?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET
            min_drop_pct = excluded.min_drop_pct,
            min_price = excluded.min_price
    """, (str(chat_id), new_drop, new_price))
    conn.commit()
    conn.close()
