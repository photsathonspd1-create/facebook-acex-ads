import sqlite3
import json
import config
from datetime import datetime
from contextlib import contextmanager

def get_db():
    conn = sqlite3.connect(config.DB_PATH)
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
    except Exception:
        conn.rollback()
        raise
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
                conditions TEXT,
                actions TEXT,
                status TEXT DEFAULT 'active',
                schedule TEXT,
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
                details TEXT,
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
                messages TEXT DEFAULT '[]',
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

        # Scaling configs
        db.execute("""
            CREATE TABLE IF NOT EXISTS scaling_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                account_id TEXT DEFAULT '',
                max_budget_increase_pct REAL DEFAULT 30,
                min_roas_threshold REAL DEFAULT 2.0,
                lookback_days INTEGER DEFAULT 7,
                kill_loss_threshold REAL DEFAULT 500,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # Experiments (A/B tests)
        db.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                account_id TEXT DEFAULT '',
                variant_a_adset_id TEXT NOT NULL,
                variant_b_adset_id TEXT NOT NULL,
                metric TEXT DEFAULT 'cpc',
                duration_days INTEGER DEFAULT 7,
                status TEXT DEFAULT 'running',
                winner TEXT,
                conclusion TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # Notification channels (Slack/Discord)
        db.execute("""
            CREATE TABLE IF NOT EXISTS notification_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                channel_type TEXT NOT NULL,
                webhook_url TEXT NOT NULL,
                name TEXT DEFAULT '',
                connected INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # Schema version tracking
        db.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                description TEXT,
                applied_at TEXT DEFAULT (datetime('now'))
            )
        """)

        db.commit()

init_db()
