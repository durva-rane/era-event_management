"""
ERA: Event Resource & Administration System
Core Database Connection Manager
"""

import contextlib
import contextvars
import logging
import mysql.connector
from core.config import Config

_after_commit = contextvars.ContextVar("era_after_commit", default=None)
_logger = logging.getLogger("era.database")


def after_commit(callback):
    """Register an external side effect for the active transaction commit."""
    callbacks = _after_commit.get()
    if callbacks is None:
        return False
    callbacks.append(callback)
    return True


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
    callbacks = []
    callback_token = _after_commit.set(callbacks)
    committed = False
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=dictionary)
        yield cursor, conn
        if commit_on_success:
            conn.commit()
            committed = True
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        _after_commit.reset(callback_token)
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
        if committed:
            for callback in callbacks:
                try:
                    callback()
                except Exception:
                    _logger.exception("Post-commit side effect failed")
