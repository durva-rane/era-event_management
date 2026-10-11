"""
ERA: Event Resource & Administration System
Core Database Connection Manager
"""

import contextlib
import mysql.connector
from core.config import Config


def get_db_connection():
    """Returns a direct MySQL connection."""
    return mysql.connector.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        charset="utf8mb4",
        collation="utf8mb4_unicode_ci",
    )


@contextlib.contextmanager
def get_db_cursor(commit_on_success=True, dictionary=True):
    """
    Context manager for database operations.
    Automatically closes cursor and connection.
    Commits on success (if commit_on_success is True) and rolls back on exception.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=dictionary)
        yield cursor, conn
        if commit_on_success:
            conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if conn:
            try:
                conn.close()
            except Exception:
                pass
