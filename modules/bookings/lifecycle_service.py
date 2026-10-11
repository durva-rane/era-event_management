"""Cross-feature booking lifecycle operations.

Callers pass their active cursor so booking, invoice, refund, and budget effects
participate in the same transaction. Finance owns the accounting implementation;
this module is the stable entry point used by event and vendor workflows.
"""

from core.db import get_db_cursor
from core.errors import AuthorizationError, ConflictError, NotFoundError, ValidationError
from core.notification_service import notify_in_transaction


def confirmed_booking_changed(cursor, booking_id, actor_id=None):
    from modules.finance.services import confirmed_booking_changed as update_financial_records
    return update_financial_records(cursor, booking_id, actor_id)


def refund_booking_in_cursor(cursor, booking_id, actor_id):
    from modules.finance.services import refund_booking_in_cursor as refund_booking
    return refund_booking(cursor, booking_id, actor_id)


def refresh_budget_alerts(cursor, event_id, actor_id=None):
    from modules.finance.services import refresh_budget_alerts as refresh_alerts
    return refresh_alerts(cursor, event_id, actor_id)


def admin_update_booking_status(booking_id, status, actor_id, actor_role, reason=None):
    """Apply an admin terminal transition with refund, audit and notifications."""
    if actor_role != "admin":
        raise AuthorizationError("Administrator privileges are required to override a booking.")
    if status not in ("rejected", "cancelled", "completed"):
        raise ValidationError("Admin booking updates may reject, cancel, or complete a booking.")
    with get_db_cursor() as (cur, _):
        cur.execute("""SELECT b.*,e.owner_id,e.organizer_id,e.name event_name
          FROM bookings b JOIN events e ON e.id=b.event_id WHERE b.id=%s FOR UPDATE""", (booking_id,))
        booking = cur.fetchone()
        if not booking:
            raise NotFoundError("Booking not found.")
        current = booking["status"]
        if status == "rejected" and current not in ("requested", "pending"):
            raise ConflictError("Only an open booking request can be rejected.")
        if status == "cancelled" and current not in ("requested", "pending", "confirmed"):
            raise ConflictError("This booking can no longer be cancelled.")
        if status == "completed" and current != "confirmed":
            raise ConflictError("Only confirmed bookings can be completed.")
        if status == "cancelled":
            refund_booking_in_cursor(cur, booking_id, actor_id)
            cur.execute("UPDATE bookings SET status='cancelled',cancelled_by=%s,cancellation_reason=%s,cancelled_at=NOW() WHERE id=%s", (actor_id, str(reason or "Cancelled by administrator")[:1000], booking_id))
            refresh_budget_alerts(cur, booking["event_id"], actor_id)
        else:
            cur.execute("UPDATE bookings SET status=%s WHERE id=%s", (status, booking_id))
            if status == "completed":
                refresh_budget_alerts(cur, booking["event_id"], actor_id)
        cur.execute("INSERT INTO audit_logs(user_id,action,entity,entity_id,result) VALUES(%s,%s,'bookings',%s,'success')", (actor_id, f"ADMIN_BOOKING_{status.upper()}", booking_id))
        recipients = {booking["owner_id"], booking["organizer_id"], booking.get("vendor_id")}
        if booking.get("venue_id"):
            cur.execute("SELECT owner_id FROM venues WHERE id=%s", (booking["venue_id"],))
            venue = cur.fetchone()
            if venue: recipients.add(venue["owner_id"])
        message = f"Booking #{booking_id} for '{booking['event_name']}' was {status} by an administrator."
        for recipient in recipients - {None, actor_id}:
            notify_in_transaction(cur, recipient, message)
        return {"success": True, "message": f"Booking #{booking_id} was {status}.", "status": status}
