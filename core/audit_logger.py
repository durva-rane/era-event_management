"""
ERA: Event Resource & Administration System
Audit Logging Service
"""

import logging
from typing import Optional
from core.db import get_db_cursor

logger = logging.getLogger("era.audit")


def log_audit(
    action: str,
    entity: str,
    entity_id: Optional[int] = None,
    user_id: Optional[int] = None,
    result: str = "success"
) -> None:
    """
    Inserts a record into the audit_logs table.
    Fails gracefully to not disrupt primary business operations.
    """
    try:
        with get_db_cursor(commit_on_success=True) as (cursor, conn):
            cursor.execute(
                """
                INSERT INTO audit_logs (user_id, action, entity, entity_id, result)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, action, entity, entity_id, result),
            )
    except Exception as exc:
        logger.warning(f"Failed to record audit log for action={action}: {exc}")
