"""
Simple database migration system for Facebook Ad Scaler.
Tracks schema version and applies migrations incrementally.
"""
import sqlite3
import logging
import config

logger = logging.getLogger('scaler.migrations')

MIGRATIONS = [
    # Version 1: Add password_hash column and schema_version table
    {
        "version": 1,
        "description": "Add schema_version table and password_hash column",
        "sql": [
            """CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                description TEXT,
                applied_at TEXT DEFAULT (datetime('now'))
            )""",
        ],
        "post": "migrate_v1_passwords",
    },
]


def get_current_version(db):
    """Get current schema version."""
    try:
        row = db.execute("SELECT MAX(version) as v FROM schema_version").fetchone()
        return row['v'] if row and row['v'] else 0
    except sqlite3.OperationalError:
        return 0


def migrate_v1_passwords(db):
    """Migrate plaintext passwords to hashed passwords."""
    try:
        # Check if password column still stores plaintext
        rows = db.execute("SELECT id, password FROM users").fetchall()
        unmigrated = [r for r in rows if ':' not in r['password'] or len(r['password']) <= 20]
        if unmigrated:
            from werkzeug.security import generate_password_hash
            for row in unmigrated:
                hashed = generate_password_hash(row['password'])
                db.execute("UPDATE users SET password = ? WHERE id = ?", (hashed, row['id']))
            logger.info(f"Migrated {len(unmigrated)} plaintext passwords to hashed")
    except Exception as e:
        logger.error(f"Password migration error: {e}")


def run_migrations():
    """Run all pending migrations."""
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    try:
        current = get_current_version(conn)
        logger.info(f"Current schema version: {current}")

        for migration in MIGRATIONS:
            if migration['version'] <= current:
                continue

            logger.info(f"Applying migration {migration['version']}: {migration['description']}")

            for sql in migration['sql']:
                conn.execute(sql)

            # Record migration
            conn.execute(
                "INSERT OR REPLACE INTO schema_version (version, description) VALUES (?, ?)",
                (migration['version'], migration['description'])
            )

            # Run post-migration function if defined
            post_fn = migration.get('post')
            if post_fn:
                globals()[post_fn](conn)

            conn.commit()
            logger.info(f"Migration {migration['version']} applied successfully")

    except Exception as e:
        logger.error(f"Migration error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    run_migrations()
    print("✅ All migrations applied")
