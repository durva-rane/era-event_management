"""
ERA: Event Resource & Administration System
Event Dispatcher & Cross-Module Hook Mechanism
"""

import logging
from typing import Callable, Dict, List
from core.audit_logger import log_audit

logger = logging.getLogger("era.events")

# Registry of event handlers
_EVENT_LISTENERS: Dict[str, List[Callable]] = {}


def register_listener(event_name: str, handler: Callable):
    """Registers an event listener callback."""
    if event_name not in _EVENT_LISTENERS:
        _EVENT_LISTENERS[event_name] = []
    _EVENT_LISTENERS[event_name].append(handler)


def send_notification(user_id: int, message: str) -> None:
    """Compatibility wrapper that routes existing modules through the shared service."""
    if not user_id or not message: return
    try:
        from core.notification_service import notify
        notify(user_id,message,event_type="system")
    except Exception as exc:
        logger.warning("Could not persist notification for user_id=%s: %s",user_id,exc)


def emit_event(event_name: str, **kwargs):
    """
    Emits an event to registered listeners.
    Executes standard audit and notification hooks.
    """
    # 1. Automatic in-app notification if targeted
    target_user_id = kwargs.get("notify_user_id") or kwargs.get("recipient_id")
    notif_msg = kwargs.get("notification_message") or kwargs.get("message")
    if target_user_id and notif_msg:
        send_notification(target_user_id, notif_msg)

    # 2. Auto-log standard audit events if specified
    if kwargs.get("audit_action"):
        log_audit(
            action=kwargs["audit_action"],
            entity=kwargs.get("audit_entity", "system"),
            entity_id=kwargs.get("audit_entity_id"),
            user_id=kwargs.get("actor_id") or kwargs.get("user_id"),
            result=kwargs.get("result", "success"),
        )

    # 3. Dispatch to custom listeners
    listeners = _EVENT_LISTENERS.get(event_name, [])
    for listener in listeners:
        try:
            listener(**kwargs)
        except Exception as exc:
            logger.error(f"Error handling event {event_name} in {listener}: {exc}")

