"""Venue booking lifecycle operations; callers provide their transaction cursor."""
from datetime import datetime, time
from decimal import Decimal
from modules.finance.services import confirmed_booking_changed, refund_booking_in_cursor, refresh_budget_alerts
from core.notification_service import notify_in_transaction


def upsert_confirmed_venue_booking(cursor, event_id, venue, day, start, end):
    cursor.execute("SELECT id,venue_id,booking_date,start_time,end_time FROM bookings WHERE event_id=%s AND booking_type='venue' AND status='confirmed' FOR UPDATE",(event_id,))
    existing=cursor.fetchone()
    hours=Decimal(str((datetime.combine(day,time.fromisoformat(end))-datetime.combine(day,time.fromisoformat(start))).total_seconds()))/Decimal(3600)
    amount=Decimal(str(venue["price_per_hour"]))*hours
    if existing:
        def db_time(value):
            if isinstance(value,time): return value.strftime("%H:%M:%S")
            return (datetime.min+value).time().strftime("%H:%M:%S")
        slot_changed=(existing["venue_id"]!=venue["id"] or existing["booking_date"]!=day or db_time(existing["start_time"])!=start or db_time(existing["end_time"])!=end)
        if slot_changed:
            cursor.execute("SELECT owner_id FROM events WHERE id=%s",(event_id,)); owner=cursor.fetchone(); actor=owner["owner_id"] if owner else None
            refund_booking_in_cursor(cursor,existing["id"],actor)
            cursor.execute("UPDATE bookings SET status='cancelled',cancelled_by=%s,cancellation_reason='Venue or event time changed',cancelled_at=NOW() WHERE id=%s",(actor,existing["id"]))
            cursor.execute("INSERT INTO audit_logs(user_id,action,entity,entity_id,result) VALUES(%s,'BOOKING_CANCELLED','bookings',%s,'success')",(actor,existing["id"]))
            cursor.execute("SELECT owner_id FROM venues WHERE id=%s",(existing["venue_id"],)); venue_owner=cursor.fetchone()
            if venue_owner: notify_in_transaction(cursor,venue_owner["owner_id"],f"Venue booking #{existing['id']} was cancelled because the event slot changed.")
            existing=None
    if existing:
        cursor.execute("UPDATE bookings SET venue_id=%s,booking_date=%s,start_time=%s,end_time=%s,amount=%s,status='confirmed' WHERE id=%s",(venue["id"],day,start,end,amount,existing["id"]))
        booking_id=existing["id"]
    else:
        cursor.execute("INSERT INTO bookings(event_id,booking_type,venue_id,booking_date,start_time,end_time,amount,status) VALUES(%s,'venue',%s,%s,%s,%s,%s,'confirmed')",(event_id,venue["id"],day,start,end,amount))
        booking_id=cursor.lastrowid
    cursor.execute("SELECT owner_id FROM events WHERE id=%s",(event_id,)); owner=cursor.fetchone()
    confirmed_booking_changed(cursor,booking_id,owner["owner_id"] if owner else None)


def _cancel_rows(cursor,event_id,booking_type=None,reason="Event cancelled"):
    type_clause=" AND booking_type=%s" if booking_type else ""
    params=(event_id,booking_type) if booking_type else (event_id,)
    cursor.execute("SELECT id,vendor_id,venue_id FROM bookings WHERE event_id=%s"+type_clause+" AND status IN ('pending','requested','confirmed') FOR UPDATE",params)
    rows=cursor.fetchall()
    cursor.execute("SELECT owner_id FROM events WHERE id=%s",(event_id,)); event=cursor.fetchone(); actor=event["owner_id"] if event else None
    for row in rows:
        refund_booking_in_cursor(cursor,row["id"],actor)
        recipient=row["vendor_id"]
        if row["venue_id"]:
            cursor.execute("SELECT owner_id FROM venues WHERE id=%s",(row["venue_id"],)); venue=cursor.fetchone()
            recipient=venue["owner_id"] if venue else recipient
        if recipient: notify_in_transaction(cursor,recipient,f"Booking #{row['id']} was cancelled: {reason}.")
        cursor.execute("INSERT INTO audit_logs(user_id,action,entity,entity_id,result) VALUES(%s,'BOOKING_CANCELLED','bookings',%s,'success')",(actor,row["id"]))
    cursor.execute("UPDATE bookings SET status='cancelled',cancelled_by=%s,cancellation_reason=%s,cancelled_at=NOW() WHERE event_id=%s"+type_clause+" AND status IN ('pending','requested','confirmed')",(actor,reason)+((booking_type,) if booking_type else ()))
    refresh_budget_alerts(cursor,event_id,actor)


def cancel_event_venue_booking(cursor,event_id):
    _cancel_rows(cursor,event_id,"venue","Venue removed from event")


def cancel_event_bookings(cursor,event_id):
    _cancel_rows(cursor,event_id,None,"Event cancelled")
