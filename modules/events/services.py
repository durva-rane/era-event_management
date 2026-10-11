"""Database operations for venues, events, schedules and venue bookings."""
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation

from core.db import get_db_cursor
from core.errors import AuthorizationError, ConflictError, NotFoundError, ValidationError
from modules.events.booking_service import cancel_event_bookings, cancel_event_venue_booking, upsert_confirmed_venue_booking
from core.notification_service import notify_in_transaction


def _time(value, field):
    try:
        parsed = time.fromisoformat(str(value))
    except (TypeError, ValueError):
        raise ValidationError(f"{field} must use HH:MM format.")
    return parsed.strftime("%H:%M:%S")


def _event_values(data):
    required = ("name", "category", "event_date", "start_time", "end_time")
    if any(not str(data.get(k, "")).strip() for k in required):
        raise ValidationError("Name, category, date, start time and end time are required.")
    try:
        day = date.fromisoformat(str(data["event_date"]))
        attendees = int(data.get("expected_attendees", 0))
    except (TypeError, ValueError):
        raise ValidationError("Date or expected attendee count is invalid.")
    start, end = _time(data["start_time"], "Start time"), _time(data["end_time"], "End time")
    if start >= end or attendees < 0:
        raise ValidationError("End time must follow start time and attendees cannot be negative.")
    return (str(data["name"]).strip(), str(data["category"]).strip(), data.get("description"), day.isoformat(), start, end, attendees)


def _authorized(event, user_id, role):
    if role == "admin":
        return
    if role == "organizer":
        allowed = event["organizer_id"] == user_id
    else:
        allowed = event["owner_id"] == user_id
    if not allowed:
        raise AuthorizationError("You cannot manage this event.")


def search_venues(filters):
    sql = "SELECT v.* FROM venues v WHERE v.status='verified'"
    params = []
    for key, op in (("location", "LIKE"), ("type", "=")):
        if filters.get(key):
            sql += f" AND v.{key} {op} %s"
            params.append(f"%{filters[key]}%" if op == "LIKE" else filters[key])
    if filters.get("capacity"):
        sql += " AND v.capacity >= %s"; params.append(int(filters["capacity"]))
    if filters.get("max_price"):
        sql += " AND v.price_per_hour <= %s"; params.append(Decimal(filters["max_price"]))
    if filters.get("date") and filters.get("start_time") and filters.get("end_time"):
        sql += " AND NOT EXISTS (SELECT 1 FROM bookings b WHERE b.venue_id=v.id AND b.booking_date=%s AND b.status='confirmed' AND b.start_time < %s AND b.end_time > %s)"
        params.extend([filters["date"], _time(filters["end_time"], "End time"), _time(filters["start_time"], "Start time")])
    sql += " ORDER BY v.price_per_hour, v.name"
    with get_db_cursor() as (cur, _):
        cur.execute(sql, tuple(params)); return cur.fetchall()


def save_venue(user_id, data, venue_id=None):
    try:
        capacity = int(data.get("capacity", 0)); price = Decimal(str(data.get("price_per_hour", "")))
    except (ValueError, InvalidOperation):
        raise ValidationError("Capacity and price must be valid numbers.")
    name, kind, location = (str(data.get(k, "")).strip() for k in ("name", "type", "location"))
    if not name or not kind or not location or capacity < 1 or price < 0:
        raise ValidationError("Name, type, location, positive capacity and nonnegative price are required.")
    with get_db_cursor() as (cur, _):
        if venue_id:
            cur.execute("SELECT owner_id FROM venues WHERE id=%s FOR UPDATE", (venue_id,)); row=cur.fetchone()
            if not row: raise NotFoundError("Venue not found.")
            if row["owner_id"] != user_id: raise AuthorizationError("You cannot edit this venue.")
            cur.execute("UPDATE venues SET name=%s,type=%s,location=%s,capacity=%s,price_per_hour=%s,status='pending' WHERE id=%s", (name,kind,location,capacity,price,venue_id))
        else:
            cur.execute("INSERT INTO venues(owner_id,name,type,location,capacity,price_per_hour,status) VALUES(%s,%s,%s,%s,%s,%s,'pending')", (user_id,name,kind,location,capacity,price)); venue_id=cur.lastrowid
    return venue_id


def list_owned_venues(user_id):
    with get_db_cursor() as (cur, _):
        cur.execute("SELECT * FROM venues WHERE owner_id=%s ORDER BY created_at DESC", (user_id,)); return cur.fetchall()


def _available_venue(cur, venue_id, day, start, end, attendees, exclude_event=None):
    # Lock the venue row to serialize all booking attempts for that venue, including
    # the empty-slot case where no booking row exists to lock.
    cur.execute("SELECT * FROM venues WHERE id=%s AND status='verified' FOR UPDATE", (venue_id,)); venue=cur.fetchone()
    if not venue: raise ConflictError("Only verified venues can be booked.")
    if venue["capacity"] < attendees: raise ConflictError("Venue capacity is below expected attendees.")
    sql="SELECT id FROM bookings WHERE venue_id=%s AND booking_date=%s AND status='confirmed' AND start_time < %s AND end_time > %s"
    args=[venue_id,day,end,start]
    if exclude_event is not None: sql += " AND event_id<>%s"; args.append(exclude_event)
    cur.execute(sql+" FOR UPDATE",tuple(args))
    if cur.fetchone(): return None
    return venue


def _alternatives(cur, day, start, end, attendees, exclude_event=None):
    sql="""SELECT v.* FROM venues v WHERE v.status='verified' AND v.capacity >= %s
      AND NOT EXISTS (SELECT 1 FROM bookings b WHERE b.venue_id=v.id AND b.booking_date=%s AND b.status='confirmed' AND b.start_time < %s AND b.end_time > %s"""
    args=[attendees,day,end,start]
    if exclude_event is not None: sql += " AND b.event_id<>%s"; args.append(exclude_event)
    sql += ") ORDER BY v.price_per_hour"
    cur.execute(sql,tuple(args)); return cur.fetchall()


def _event_row(cur,event_id):
    cur.execute("SELECT * FROM events WHERE id=%s FOR UPDATE",(event_id,)); event=cur.fetchone()
    if not event: raise NotFoundError("Event not found.")
    return event


def save_event(user_id, role, data, event_id=None):
    values=_event_values(data); venue_id=data.get("venue_id") or None
    try: venue_id=int(venue_id) if venue_id else None
    except (TypeError,ValueError): raise ValidationError("Venue id is invalid.")
    organizer_id=data.get("organizer_id") or None
    try: organizer_id=int(organizer_id) if organizer_id else None
    except (TypeError,ValueError): raise ValidationError("Organizer id is invalid.")
    if not event_id and role == "organizer":
        organizer_id = user_id
    with get_db_cursor() as (cur, _):
        existing=_event_row(cur,event_id) if event_id else None
        if existing: _authorized(existing,user_id,role)
        owner=existing["owner_id"] if existing else user_id
        if not existing and role not in ("client","organizer","admin"): raise AuthorizationError("Only clients and organizers can create events.")
        selected=venue_id if venue_id is not None else (existing["venue_id"] if existing else None)
        venue=None
        if selected:
            try: venue=_available_venue(cur,selected,values[3],values[4],values[5],values[6],event_id)
            except ConflictError as exc:
                if "capacity" in exc.message:
                    raise ConflictError(exc.message, payload={"alternatives":_alternatives(cur,values[3],values[4],values[5],values[6],event_id)})
                raise ConflictError(exc.message,payload={"alternatives":_alternatives(cur,values[3],values[4],values[5],values[6],event_id)})
            if not venue:
                raise ConflictError("Venue is unavailable for that time slot.",payload={"alternatives":_alternatives(cur,values[3],values[4],values[5],values[6],event_id)})
        vals=(values[0],values[1],values[2],values[3],values[4],values[5],values[6],selected,organizer_id)
        if existing:
            cur.execute("UPDATE events SET name=%s,category=%s,description=%s,event_date=%s,start_time=%s,end_time=%s,expected_attendees=%s,venue_id=%s,organizer_id=COALESCE(%s,organizer_id),status='planned' WHERE id=%s",vals+(event_id,))
            if selected: upsert_confirmed_venue_booking(cur,event_id,venue,values[3],values[4],values[5])
            else: cancel_event_venue_booking(cur,event_id)
            _notify(cur,owner,f"Event '{values[0]}' was updated.")
            if existing["organizer_id"]: _notify(cur,existing["organizer_id"],f"Assigned event '{values[0]}' was updated.")
            return event_id
        cur.execute("INSERT INTO events(owner_id,organizer_id,venue_id,name,category,description,event_date,start_time,end_time,expected_attendees,status) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'planned')",(owner,organizer_id,selected)+values[:2]+(values[2],values[3],values[4],values[5],values[6]))
        new_id=cur.lastrowid
        if selected: upsert_confirmed_venue_booking(cur,new_id,venue,values[3],values[4],values[5])
        return new_id


def _notify(cur,user_id,message):
    notify_in_transaction(cur,user_id,message)


def change_event_status(user_id,role,event_id,status):
    with get_db_cursor() as (cur,_):
        event=_event_row(cur,event_id); _authorized(event,user_id,role)
        cur.execute("UPDATE events SET status=%s,live_status=%s WHERE id=%s",(status,"cancelled" if status=="cancelled" else event["live_status"],event_id))
        # Booking lifecycle is a service operation in the same transaction, before notifications.
        cancel_event_bookings(cur,event_id)
        _notify(cur,event["owner_id"],f"Event '{event['name']}' was {status}.")
        if event["organizer_id"]: _notify(cur,event["organizer_id"],f"Assigned event '{event['name']}' was {status}.")


def list_events(user_id,role,filters=None):
    filters=filters or {}; sql="SELECT e.*,v.name AS venue_name FROM events e LEFT JOIN venues v ON v.id=e.venue_id WHERE 1=1"; args=[]
    if role=="client": sql+=" AND e.owner_id=%s"; args.append(user_id)
    elif role=="organizer": sql+=" AND e.organizer_id=%s"; args.append(user_id)
    elif role!="admin": return []
    if filters.get("start"): sql+=" AND e.event_date >= %s"; args.append(filters["start"])
    if filters.get("end"): sql+=" AND e.event_date <= %s"; args.append(filters["end"])
    sql+=" ORDER BY e.event_date,e.start_time"
    with get_db_cursor() as (cur,_): cur.execute(sql,tuple(args)); return cur.fetchall()


def event_details(user_id,role,event_id):
    with get_db_cursor() as (cur,_):
        cur.execute("SELECT e.*,v.name AS venue_name,v.location AS venue_location FROM events e LEFT JOIN venues v ON v.id=e.venue_id WHERE e.id=%s",(event_id,)); event=cur.fetchone()
        if not event: raise NotFoundError("Event not found.")
        _authorized(event,user_id,role)
        cur.execute("SELECT * FROM event_schedule_items WHERE event_id=%s ORDER BY start_time",(event_id,)); event["schedule"]=cur.fetchall()
        return event


def schedule_action(user_id,role,event_id,item_id,data=None,delete=False):
    data=data or {}
    with get_db_cursor() as (cur,_):
        event=_event_row(cur,event_id); _authorized(event,user_id,role)
        if delete:
            cur.execute("DELETE FROM event_schedule_items WHERE id=%s AND event_id=%s",(item_id,event_id))
            if not cur.rowcount: raise NotFoundError("Schedule item not found.")
            action="SCHEDULE_ITEM_DELETED"
            item_title="schedule item"
            target=item_id
        else:
            title=str(data.get("title","")).strip(); start=_time(data.get("start_time"),"Start time"); end=_time(data.get("end_time"),"End time")
            if not title or start>=end: raise ValidationError("Schedule title and a valid time range are required.")
            if item_id:
                cur.execute("UPDATE event_schedule_items SET title=%s,start_time=%s,end_time=%s WHERE id=%s AND event_id=%s",(title,start,end,item_id,event_id))
                if not cur.rowcount: raise NotFoundError("Schedule item not found.")
                action="SCHEDULE_ITEM_UPDATED"; target=item_id
            else:
                cur.execute("INSERT INTO event_schedule_items(event_id,title,start_time,end_time) VALUES(%s,%s,%s,%s)",(event_id,title,start,end)); item_id=cur.lastrowid
                action="SCHEDULE_ITEM_CREATED"; target=item_id
            item_title=title
        cur.execute("INSERT INTO audit_logs(user_id,action,entity,entity_id,result) VALUES(%s,%s,'event_schedule_items',%s,'success')",(user_id,action,target))
        _notify(cur,event["owner_id"],f"Schedule change: {item_title} was changed for event '{event['name']}'.")
        if event["organizer_id"] and event["organizer_id"]!=event["owner_id"]: _notify(cur,event["organizer_id"],f"Schedule change: {item_title} was changed for event '{event['name']}'.")
        return target
