import sqlite3
import json
from datetime import datetime
from contextlib import contextmanager

DB_PATH = 'scaler.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

@contextmanager
def db_conn():
    conn = get_db()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with db_conn() as db:
        # Users
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                name TEXT NOT NULL,
                fb_token TEXT,
                role TEXT DEFAULT 'admin',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # Settings
        db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                user_id INTEGER,
                key TEXT,
                value TEXT,
                PRIMARY KEY (user_id, key)
            )
        """)

        # Rules
        db.execute("""
            CREATE TABLE IF NOT EXISTS rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                description TEXT,
                account_id TEXT,
                conditions TEXT,  -- JSON
                actions TEXT,     -- JSON
                status TEXT DEFAULT 'active',
                schedule TEXT,    -- JSON (check interval, etc.)
                last_run TEXT,
                run_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # Bot Actions (audit trail)
        db.execute("""
            CREATE TABLE IF NOT EXISTS bot_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                rule_id INTEGER,
                action_type TEXT NOT NULL,
                target_type TEXT,
                target_id TEXT,
                target_name TEXT,
                details TEXT,  -- JSON
                undoable INTEGER DEFAULT 1,
                undone INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # Conversations (AdsGPT)
        db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT DEFAULT 'New Chat',
                messages TEXT DEFAULT '[]',  -- JSON array
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # Team members
        db.execute("""
            CREATE TABLE IF NOT EXISTS team_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER,
                user_id INTEGER,
                role TEXT DEFAULT 'viewer',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # Team invites
        db.execute("""
            CREATE TABLE IF NOT EXISTS team_invites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER,
                email TEXT NOT NULL,
                role TEXT DEFAULT 'viewer',
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # Telegram connections
        db.execute("""
            CREATE TABLE IF NOT EXISTS telegram_connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                account_id TEXT,
                chat_id TEXT,
                bot_token TEXT,
                connected INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # Notification settings
        db.execute("""
            CREATE TABLE IF NOT EXISTS notification_settings (
                user_id INTEGER PRIMARY KEY,
                email_enabled INTEGER DEFAULT 1,
                telegram_enabled INTEGER DEFAULT 0,
                rules_fired INTEGER DEFAULT 1,
                budget_alerts INTEGER DEFAULT 1,
                daily_summary INTEGER DEFAULT 0,
                settings_json TEXT DEFAULT '{}'
            )
        """)

        # Tracking
        db.execute("""
            CREATE TABLE IF NOT EXISTS tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                page TEXT,
                error TEXT,
                user_agent TEXT,
                metadata TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        db.commit()

init_db()
