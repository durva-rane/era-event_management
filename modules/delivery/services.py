"""Delivery task assignment, status workflow, partner availability and tracking."""
from datetime import datetime

from core.db import get_db_cursor
from core.errors import AuthorizationError, ConflictError, NotFoundError, ValidationError
from core.notification_service import notify_in_transaction
from core.pagination import page_args

TRANSITIONS = {
    "assigned": {"accepted", "rejected", "cancelled"},
    "accepted": {"pickup_pending", "failed", "cancelled"},
    "pickup_pending": {"picked_up", "failed", "cancelled"},
    "picked_up": {"in_transit", "failed"},
    "in_transit": {"delivered", "failed"},
    "delivered": set(), "rejected": set(), "failed": set(), "cancelled": set(),
}


def _audit(cur, user_id, action, task_id):
    cur.execute("INSERT INTO audit_logs(user_id,action,entity,entity_id,result) VALUES(%s,%s,'delivery_tasks',%s,'success')", (user_id, action, task_id))


def _event(cur, event_id, user_id, role, lock=True):
    cur.execute(f"SELECT * FROM events WHERE id=%s{' FOR UPDATE' if lock else ''}", (event_id,))
    event = cur.fetchone()
    if not event:
        raise NotFoundError("Event not found.")
    if role not in ("admin", "organizer") or (role != "admin" and event["organizer_id"] != user_id):
        raise AuthorizationError("Only the assigned organizer or an admin can manage delivery for this event.")
    return event


def _partner_available(cur, partner_id, scheduled_at, exclude_task=None, lock=False):
    cur.execute("""SELECT u.id,u.name,u.phone FROM users u JOIN delivery_partners d ON d.user_id=u.id
      WHERE u.id=%s AND u.role='delivery_partner' AND u.status='active' AND d.status='active' AND d.availability='available'""" + (" FOR UPDATE" if lock else ""), (partner_id,))
    partner = cur.fetchone()
    if not partner:
        return None
    # Delivery tasks have a scheduled point but no duration; reserve the partner for that calendar day.
    sql = "SELECT id FROM delivery_tasks WHERE partner_id=%s AND DATE(scheduled_at)=DATE(%s) AND status IN ('assigned','accepted','pickup_pending','picked_up','in_transit')"
    params = [partner_id, scheduled_at]
    if exclude_task:
        sql += " AND id<>%s"; params.append(exclude_task)
    sql += " LIMIT 1 FOR UPDATE"
    cur.execute(sql, tuple(params))
    if cur.fetchone():
        return None
    return partner


def suggest_partners(event_id, user_id, role, scheduled_at):
    when = _parse_datetime(scheduled_at)
    with get_db_cursor(commit_on_success=False) as (cur, _):
        _event(cur, event_id, user_id, role, lock=False)
        cur.execute("""SELECT u.id,u.name,u.phone,d.availability FROM users u JOIN delivery_partners d ON d.user_id=u.id
        WHERE u.role='delivery_partner' AND u.status='active' AND d.status='active' AND d.availability='available'
        AND NOT EXISTS(SELECT 1 FROM delivery_tasks t WHERE t.partner_id=u.id AND DATE(t.scheduled_at)=DATE(%s)
          AND t.status IN ('assigned','accepted','pickup_pending','picked_up','in_transit')) ORDER BY u.name""", (when,))
        return cur.fetchall()


def _parse_datetime(value):
    try:
        parsed = datetime.fromisoformat(str(value).strip())
    except (TypeError, ValueError):
        raise ValidationError("Date and time must be a valid local datetime.")
    if parsed <= datetime.now():
        raise ValidationError("Delivery date and time must be in the future.")
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def create_task(event_id, user_id, role, data):
    pickup = str(data.get("pickup", "")).strip()
    destination = str(data.get("destination", "")).strip()
    description = str(data.get("item_description", "")).strip()
    instructions = str(data.get("instructions", "")).strip() or None
    partner_id = data.get("partner_id")
    try:
        partner_id = int(partner_id)
        quantity = int(data.get("quantity", 1))
    except (TypeError, ValueError):
        raise ValidationError("Choose a delivery partner and enter a valid quantity.")
    scheduled_at = _parse_datetime(data.get("scheduled_at"))
    if not pickup or not destination or not description or len(pickup) > 255 or len(destination) > 255 or quantity < 1:
        raise ValidationError("Pickup, destination, item description and positive quantity are required.")
    with get_db_cursor() as (cur, _):
        event = _event(cur, event_id, user_id, role)
        partner = _partner_available(cur, partner_id, scheduled_at, lock=True)
        if not partner:
            raise ConflictError("That delivery partner is unavailable for this date. Refresh suggestions.")
        cur.execute("INSERT INTO delivery_tasks(event_id,partner_id,pickup,destination,scheduled_at,item_description,quantity,instructions,status) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,'assigned')", (event_id, partner_id, pickup, destination, scheduled_at, description, quantity, instructions))
        task_id = cur.lastrowid
        _timeline(cur, task_id, "assigned", None, "assigned", "Task created and assigned", user_id)
        _audit(cur, user_id, "DELIVERY_TASK_ASSIGNED", task_id)
        notify_in_transaction(cur, partner_id, f"Delivery task #{task_id} was assigned for event {event['name']}.", event_type="delivery_update", link="/delivery/tasks")
        return task_id


def _timeline(cur, task_id, update_type, from_status, to_status, note, actor_id):
    cur.execute("INSERT INTO delivery_task_updates(task_id,update_type,from_status,to_status,note,actor_id) VALUES(%s,%s,%s,%s,%s,%s)", (task_id, update_type, from_status, to_status, note, actor_id))


def _task(cur, task_id, lock=True):
    cur.execute(f"""SELECT t.*,e.name event_name,e.owner_id,e.organizer_id,u.name partner_name
      FROM delivery_tasks t JOIN events e ON e.id=t.event_id LEFT JOIN users u ON u.id=t.partner_id WHERE t.id=%s{' FOR UPDATE' if lock else ''}""", (task_id,))
    task = cur.fetchone()
    if not task:
        raise NotFoundError("Delivery task not found.")
    return task


def assign_task(task_id, admin_or_organizer_id, role, partner_id):
    try:
        partner_id = int(partner_id)
    except (TypeError, ValueError):
        raise ValidationError("A delivery partner is required.")
    with get_db_cursor() as (cur, _):
        task = _task(cur, task_id)
        _event(cur, task["event_id"], admin_or_organizer_id, role)
        if task["status"] != "assigned":
            raise ConflictError("A task can only be reassigned before the partner responds.")
        if task["partner_id"] == partner_id:
            return task_id
        partner = _partner_available(cur, partner_id, task["scheduled_at"], exclude_task=task_id, lock=True)
        if not partner:
            raise ConflictError("That delivery partner is unavailable for this date.")
        old_partner = task["partner_id"]
        cur.execute("UPDATE delivery_tasks SET partner_id=%s WHERE id=%s", (partner_id, task_id))
        _timeline(cur, task_id, "assigned", "assigned", "assigned", "Task reassigned", admin_or_organizer_id)
        _audit(cur, admin_or_organizer_id, "DELIVERY_TASK_REASSIGNED", task_id)
        notify_in_transaction(cur, partner_id, f"Delivery task #{task_id} was assigned to you.", event_type="delivery_update", link="/delivery/tasks")
        if old_partner:
            notify_in_transaction(cur, old_partner, f"Delivery task #{task_id} has been reassigned.", event_type="delivery_update")
        return task_id


def list_partner_tasks(partner_id, filters=None):
    page,size,offset=page_args(filters or {})
    with get_db_cursor(commit_on_success=False) as (cur, _):
        cur.execute("""SELECT t.*,e.name event_name FROM delivery_tasks t JOIN events e ON e.id=t.event_id
        WHERE t.partner_id=%s ORDER BY t.scheduled_at,t.id LIMIT %s OFFSET %s""", (partner_id,size,offset))
        return cur.fetchall()


def organizer_events(user_id, filters=None):
    page,size,offset=page_args(filters or {})
    with get_db_cursor(commit_on_success=False) as (cur, _):
        cur.execute("SELECT id,name,event_date,status FROM events WHERE organizer_id=%s ORDER BY event_date DESC LIMIT %s OFFSET %s", (user_id,size,offset))
        return cur.fetchall()


def list_event_tasks(event_id, user_id, role, filters=None):
    page,size,offset=page_args(filters or {})
    with get_db_cursor(commit_on_success=False) as (cur, _):
        _event(cur, event_id, user_id, role, lock=False)
        cur.execute("""SELECT t.*,u.name partner_name FROM delivery_tasks t LEFT JOIN users u ON u.id=t.partner_id
        WHERE t.event_id=%s ORDER BY t.scheduled_at,t.id LIMIT %s OFFSET %s""", (event_id,size,offset))
        return cur.fetchall()


def tracking(task_id, user_id, role):
    with get_db_cursor(commit_on_success=False) as (cur, _):
        task = _task(cur, task_id, lock=False)
        if role not in ("admin", "organizer") or (role != "admin" and task["organizer_id"] != user_id):
            raise AuthorizationError("Only the assigned organizer can view this delivery timeline.")
        cur.execute("SELECT x.*,u.name actor_name FROM delivery_task_updates x LEFT JOIN users u ON u.id=x.actor_id WHERE x.task_id=%s ORDER BY x.created_at,x.id", (task_id,))
        return task, cur.fetchall()


def update_status(task_id, actor_id, role, status, note=None):
    if status not in TRANSITIONS:
        raise ValidationError("Unknown delivery status.")
    with get_db_cursor() as (cur, _):
        task = _task(cur, task_id)
        if role == "delivery_partner":
            if task["partner_id"] != actor_id:
                raise AuthorizationError("You can only update tasks assigned to you.")
        elif role in ("organizer", "admin"):
            _event(cur, task["event_id"], actor_id, role)
            if status != "cancelled":
                raise AuthorizationError("Organizers and admins can only cancel delivery tasks.")
        else:
            raise AuthorizationError("You cannot update this delivery task.")
        if status not in TRANSITIONS[task["status"]]:
            raise ConflictError(f"Cannot move a task from {task['status']} to {status}.")
        cur.execute("UPDATE delivery_tasks SET status=%s WHERE id=%s", (status, task_id))
        if status == "accepted":
            cur.execute("UPDATE delivery_partners SET availability='busy',status='on_delivery' WHERE user_id=%s", (task["partner_id"],))
        elif status in ("rejected", "delivered", "failed", "cancelled"):
            cur.execute("UPDATE delivery_partners SET availability='available',status='active' WHERE user_id=%s AND status='on_delivery'", (task["partner_id"],))
        _timeline(cur, task_id, "status", task["status"], status, str(note or "").strip() or None, actor_id)
        _audit(cur, actor_id, f"DELIVERY_STATUS_{status.upper()}", task_id)
        msg = f"Delivery task #{task_id} for {task['event_name']} is now {status.replace('_',' ')}."
        for host in {task["owner_id"], task["organizer_id"]} - {None}:
            notify_in_transaction(cur, host, msg, event_type="delivery_update", link=f"/events/{task['event_id']}/deliveries")
        return status


def report_delay(task_id, partner_id, message):
    text = str(message or "").strip()
    if not text:
        raise ValidationError("Add a short delay explanation.")
    with get_db_cursor() as (cur, _):
        task = _task(cur, task_id)
        if task["partner_id"] != partner_id:
            raise AuthorizationError("You can only report delays for tasks assigned to you.")
        if task["status"] not in ("accepted", "pickup_pending", "picked_up", "in_transit"):
            raise ConflictError("Delay reports are unavailable at this stage.")
        _timeline(cur, task_id, "delayed", task["status"], task["status"], text, partner_id)
        _audit(cur, partner_id, "DELIVERY_DELAY_REPORTED", task_id)
        for host in {task["owner_id"], task["organizer_id"]} - {None}:
            notify_in_transaction(cur, host, f"Delivery task #{task_id} is delayed: {text}", event_type="delivery_update", link=f"/events/{task['event_id']}/deliveries")
        return True


def manage_partner(user_id, partner_id, data):
    availability = data.get("availability")
    status = data.get("status")
    if availability not in ("available", "busy", "offline") or status not in ("active", "inactive", "on_delivery"):
        raise ValidationError("Partner availability or status is invalid.")
    with get_db_cursor() as (cur, _):
        cur.execute("SELECT user_id FROM delivery_partners WHERE user_id=%s FOR UPDATE", (partner_id,))
        if not cur.fetchone():
            raise NotFoundError("Delivery partner not found.")
        cur.execute("UPDATE delivery_partners SET availability=%s,status=%s WHERE user_id=%s", (availability, status, partner_id))
        _audit(cur, user_id, "DELIVERY_PARTNER_UPDATED", partner_id)
        notify_in_transaction(cur, partner_id, f"Your delivery partner profile was set to {status} / {availability}.", event_type="delivery_update")
        return True
