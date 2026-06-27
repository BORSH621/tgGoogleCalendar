import sqlite3
import json
import os

DB_NAME = "bot_data.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                reminder_minutes INTEGER DEFAULT 15,
                credentials TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sent_reminders (
                user_id INTEGER,
                event_id TEXT,
                PRIMARY KEY (user_id, event_id)
            )
        """)
        # Таблица истории прошедших встреч
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meeting_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT,
                end_time TEXT
            )
        """)
        conn.commit()

def get_user(user_id):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT reminder_minutes, credentials FROM users WHERE user_id = ?", (user_id,))
        return cursor.fetchone()

def save_user_credentials(user_id, creds_json):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (user_id, credentials) 
            VALUES (?, ?) 
            ON CONFLICT(user_id) DO UPDATE SET credentials = excluded.credentials
        """, (user_id, creds_json))
        conn.commit()

def update_reminder(user_id, minutes):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (user_id, reminder_minutes) 
            VALUES (?, ?) 
            ON CONFLICT(user_id) DO UPDATE SET reminder_minutes = excluded.reminder_minutes
        """, (user_id, minutes))
        conn.commit()

def is_reminder_sent(user_id, event_id):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM sent_reminders WHERE user_id = ? AND event_id = ?", (user_id, event_id))
        return cursor.fetchone() is not None

def mark_reminder_as_sent(user_id, event_id):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO sent_reminders (user_id, event_id) VALUES (?, ?)", (user_id, event_id))
        conn.commit()

def add_to_history(user_id, title, end_time):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO meeting_history (user_id, title, end_time) VALUES (?, ?, ?)", (user_id, title, end_time))
        cursor.execute("""
            DELETE FROM meeting_history 
            WHERE user_id = ? AND id NOT IN (
                SELECT id FROM meeting_history WHERE user_id = ? ORDER BY end_time DESC LIMIT 10
            )
        """, (user_id, user_id))
        conn.commit()

def get_history(user_id):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT title, end_time FROM meeting_history WHERE user_id = ? ORDER BY end_time DESC LIMIT 10", (user_id,))
        return cursor.fetchall()

def get_all_authenticated_users():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, reminder_minutes, credentials FROM users WHERE credentials IS NOT NULL")
        return cursor.fetchall()