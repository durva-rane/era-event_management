"""
ERA: Event Resource & Administration System
Core Framework Package
"""

from core.config import Config
from core.db import get_db_connection, get_db_cursor
from core.decorators import login_required, role_required, verified_required
from core.audit_logger import log_audit
from core.events import emit_event

__all__ = [
    "Config",
    "get_db_connection",
    "get_db_cursor",
    "login_required",
    "role_required",
    "verified_required",
    "log_audit",
    "emit_event",
]
