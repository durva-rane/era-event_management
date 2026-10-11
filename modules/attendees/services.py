"""Guest list, RSVP, event check-in and reminder operations."""
import csv
import io
import re
import secrets
from datetime import datetime, timedelta

from core.config import Config
from core.db import get_db_cursor
from core.errors import AuthorizationError, ConflictError, NotFoundError, ValidationError
from core.notification_service import notify_in_transaction

EMAIL_RE=re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _audit(cur,user_id,action,entity,entity_id):
    cur.execute("INSERT INTO audit_logs(user_id,action,entity,entity_id,result) VALUES(%s,%s,%s,%s,'success')",(user_id,action,entity,entity_id))


def _event_access(cur,event_id,user_id,role):
    cur.execute("SELECT e.*,v.name venue_name,v.location venue_location FROM events e LEFT JOIN venues v ON v.id=e.venue_id WHERE e.id=%s FOR UPDATE",(event_id,)); event=cur.fetchone()
    if not event: raise NotFoundError("Event not found.")
    if role!="admin" and not (role=="organizer" and event["organizer_id"]==user_id):
        raise AuthorizationError("Only the event's assigned organizer can manage attendees.")
    return event


def _validate_guest(name,email,phone):
    name=str(name or "").strip(); email=str(email or "").strip().lower(); phone=str(phone or "").strip() or None
    if not name or len(name)>120: raise ValidationError("Name is required and must be no longer than 120 characters.")
    if len(email)>255 or not EMAIL_RE.match(email): raise ValidationError("A valid email address is required.")
    if phone and len(phone)>20: raise ValidationError("Phone must be no longer than 20 characters.")
    return name,email,phone


def _send_invitation(cur,event,attendee_id,name,email,phone,token):
    link=f"{Config.PUBLIC_BASE_URL.rstrip('/')}/rsvp/{token}"
    cur.execute("SELECT id FROM users WHERE email=%s",(email,)); user=cur.fetchone()
    notify_in_transaction(cur,user["id"] if user else None,
        f"You are invited to {event['name']} on {event['event_date']} at {event['start_time']}. RSVP here: {link}",
        event_type="invitation",link=link,email_to=email,phone=phone,subject=f"Invitation: {event['name']}")


def add_attendee(user_id,role,event_id,data):
    name,email,phone=_validate_guest(data.get("name"),data.get("email"),data.get("phone")); token=secrets.token_urlsafe(32)
    with get_db_cursor() as (cur,_):
        event=_event_access(cur,event_id,user_id,role)
        cur.execute("SELECT id FROM attendees WHERE event_id=%s AND LOWER(email)=LOWER(%s)",(event_id,email))
        if cur.fetchone(): raise ConflictError("This guest is already on the event list.")
        cur.execute("INSERT INTO attendees(event_id,name,email,phone,rsvp_token) VALUES(%s,%s,%s,%s,%s)",(event_id,name,email,phone,token)); attendee_id=cur.lastrowid
        _send_invitation(cur,event,attendee_id,name,email,phone,token); _audit(cur,user_id,"ATTENDEE_INVITED","attendees",attendee_id)
        return attendee_id,token


def edit_attendee(user_id,role,event_id,attendee_id,data):
    name,email,phone=_validate_guest(data.get("name"),data.get("email"),data.get("phone"))
    with get_db_cursor() as (cur,_):
        event=_event_access(cur,event_id,user_id,role)
        cur.execute("SELECT * FROM attendees WHERE id=%s AND event_id=%s FOR UPDATE",(attendee_id,event_id)); old=cur.fetchone()
        if not old: raise NotFoundError("Attendee not found.")
        cur.execute("SELECT id FROM attendees WHERE event_id=%s AND LOWER(email)=LOWER(%s) AND id<>%s",(event_id,email,attendee_id))
        if cur.fetchone(): raise ConflictError("Another event guest already uses this email.")
        changed_email=email!=old["email"].lower(); token=secrets.token_urlsafe(32) if changed_email else old["rsvp_token"]
        cur.execute("UPDATE attendees SET name=%s,email=%s,phone=%s,rsvp_token=%s WHERE id=%s",(name,email,phone,token,attendee_id))
        _audit(cur,user_id,"ATTENDEE_UPDATED","attendees",attendee_id)
        if changed_email: _send_invitation(cur,event,attendee_id,name,email,phone,token)
        else:
            cur.execute("SELECT id FROM users WHERE email=%s",(email,)); guest=cur.fetchone()
            if guest: notify_in_transaction(cur,guest["id"],f"Your invitation details for {event['name']} were updated.",event_type="invitation")
        return attendee_id


def remove_attendee(user_id,role,event_id,attendee_id):
    with get_db_cursor() as (cur,_):
        event=_event_access(cur,event_id,user_id,role)
        cur.execute("SELECT * FROM attendees WHERE id=%s AND event_id=%s FOR UPDATE",(attendee_id,event_id)); attendee=cur.fetchone()
        if not attendee: raise NotFoundError("Attendee not found.")
        cur.execute("SELECT id FROM users WHERE email=%s",(attendee["email"],)); user=cur.fetchone()
        cur.execute("DELETE FROM attendees WHERE id=%s",(attendee_id,)); _audit(cur,user_id,"ATTENDEE_REMOVED","attendees",attendee_id)
        notify_in_transaction(cur,user["id"] if user else None,f"Your invitation to {event['name']} was cancelled.",event_type="cancellation",email_to=attendee["email"],phone=attendee["phone"],subject=f"Invitation cancelled: {event['name']}")


def import_csv(user_id,role,event_id,file_stream):
    try: content=file_stream.read().decode("utf-8-sig")
    except (AttributeError,UnicodeDecodeError): raise ValidationError("Upload a UTF-8 CSV file.")
    reader=csv.DictReader(io.StringIO(content))
    if not reader.fieldnames: raise ValidationError("CSV needs a header row with name and email columns.")
    headers={str(name or "").strip().lower() for name in reader.fieldnames}
    if not {"name","email"}.issubset(headers): raise ValidationError("CSV must contain name and email columns; phone is optional.")
    report={"created":0,"duplicates":0,"errors":[]}
    with get_db_cursor() as (cur,_):
        event=_event_access(cur,event_id,user_id,role)
        cur.execute("SELECT LOWER(email) email FROM attendees WHERE event_id=%s",(event_id,)); known={row["email"] for row in cur.fetchall()}
        for line,row in enumerate(reader,start=2):
            if line>5001:
                report["errors"].append({"row":line,"error":"CSV row limit is 5000."}); break
            normalized={str(key or "").strip().lower():value for key,value in row.items()}
            try: name,email,phone=_validate_guest(normalized.get("name"),normalized.get("email"),normalized.get("phone"))
            except ValidationError as exc:
                report["errors"].append({"row":line,"error":exc.message}); continue
            if email in known:
                report["duplicates"]+=1; continue
            token=secrets.token_urlsafe(32)
            cur.execute("INSERT INTO attendees(event_id,name,email,phone,rsvp_token) VALUES(%s,%s,%s,%s,%s)",(event_id,name,email,phone,token)); attendee_id=cur.lastrowid
            _send_invitation(cur,event,attendee_id,name,email,phone,token); _audit(cur,user_id,"ATTENDEE_INVITED","attendees",attendee_id)
            known.add(email); report["created"]+=1
    return report


def guest_list(user_id,role,event_id):
    with get_db_cursor(commit_on_success=False) as (cur,_):
        event=_event_access(cur,event_id,user_id,role)
        cur.execute("SELECT id,event_id,name,email,phone,invitation_status,rsvp_status,checked_in_at,checked_out_at,created_at FROM attendees WHERE event_id=%s ORDER BY name",(event_id,)); return cur.fetchall()


def rsvp_page_data(token):
    with get_db_cursor(commit_on_success=False) as (cur,_):
        cur.execute("SELECT a.id attendee_id,a.name attendee_name,a.rsvp_status,e.id event_id,e.name event_name,e.category,e.description,e.event_date,e.start_time,e.end_time,v.name venue_name,v.location venue_location FROM attendees a JOIN events e ON e.id=a.event_id LEFT JOIN venues v ON v.id=e.venue_id WHERE a.rsvp_token=%s",(token,)); row=cur.fetchone()
        if not row: raise NotFoundError("This RSVP link is invalid.")
        return row


def submit_rsvp(token,status):
    if status not in ("accepted","declined","maybe"): raise ValidationError("RSVP must be accepted, declined or maybe.")
    with get_db_cursor() as (cur,_):
        cur.execute("SELECT a.*,e.name event_name,e.event_date,e.start_time FROM attendees a JOIN events e ON e.id=a.event_id WHERE a.rsvp_token=%s FOR UPDATE",(token,)); row=cur.fetchone()
        if not row: raise NotFoundError("This RSVP link is invalid.")
        invitation="registered" if status=="accepted" else ("declined" if status=="declined" else "invited")
        cur.execute("UPDATE attendees SET rsvp_status=%s,invitation_status=%s WHERE id=%s",(status,invitation,row["id"]))
        _audit(cur,None,"ATTENDEE_RSVP_UPDATED","attendees",row["id"])
        cur.execute("SELECT id FROM users WHERE email=%s",(row["email"],)); user=cur.fetchone()
        notify_in_transaction(cur,user["id"] if user else None,f"RSVP recorded as {status} for {row['event_name']}.",event_type="rsvp_confirmation",email_to=row["email"],phone=row["phone"],subject=f"RSVP received: {row['event_name']}")
        cur.execute("SELECT owner_id,organizer_id FROM events WHERE id=%s",(row["event_id"],)); hosts=cur.fetchone()
        for host in {hosts["owner_id"],hosts["organizer_id"]}-{None}: notify_in_transaction(cur,host,f"{row['name']} responded {status} to {row['event_name']}.",event_type="rsvp_confirmation")
        return {"status":status,"event_name":row["event_name"]}


def attendee_invitations(email):
    with get_db_cursor(commit_on_success=False) as (cur,_):
        cur.execute("""SELECT a.id,a.name,a.email,a.invitation_status,a.rsvp_status,a.checked_in_at,a.checked_out_at,
        e.id event_id,e.name event_name,e.category,e.description,e.event_date,e.start_time,e.end_time,v.name venue_name,v.location venue_location
        FROM attendees a JOIN events e ON e.id=a.event_id LEFT JOIN venues v ON v.id=e.venue_id WHERE LOWER(a.email)=LOWER(%s) ORDER BY e.event_date""",(email,)); return cur.fetchall()


def check_in(user_id,role,event_id,attendee_id,checkout=False):
    with get_db_cursor() as (cur,_):
        event=_event_access(cur,event_id,user_id,role)
        cur.execute("SELECT id,name,checked_in_at,checked_out_at FROM attendees WHERE id=%s AND event_id=%s FOR UPDATE",(attendee_id,event_id)); row=cur.fetchone()
        if not row: raise NotFoundError("Attendee not found.")
        if checkout:
            if not row["checked_in_at"]: raise ConflictError("Check in this attendee before checking them out.")
            if row["checked_out_at"]: raise ConflictError("This attendee has already checked out.")
            cur.execute("UPDATE attendees SET checked_out_at=NOW() WHERE id=%s",(attendee_id,)); action="ATTENDEE_CHECKED_OUT"; message=f"{row['name']} checked out."
        else:
            if row["checked_in_at"]: raise ConflictError("This attendee has already checked in.")
            cur.execute("UPDATE attendees SET checked_in_at=NOW() WHERE id=%s",(attendee_id,)); action="ATTENDEE_CHECKED_IN"; message=f"{row['name']} checked in."
        _audit(cur,user_id,action,"attendees",attendee_id)
        for host in {event.get("owner_id"),event.get("organizer_id")} - {None}:
            notify_in_transaction(cur,host,message,event_type="attendee_checkin")
        return message


def live_summary(user_id,role,event_id):
    with get_db_cursor(commit_on_success=False) as (cur,_):
        _event_access(cur,event_id,user_id,role)
        cur.execute("""SELECT COUNT(*) invited,SUM(rsvp_status='accepted') confirmed,SUM(rsvp_status='declined') declined,
        SUM(rsvp_status IN ('pending','maybe')) pending,SUM(checked_in_at IS NOT NULL) checked_in
        FROM attendees WHERE event_id=%s""",(event_id,)); row=cur.fetchone()
        invited=int(row["invited"] or 0); checked=int(row["checked_in"] or 0)
        return {"invited":invited,"confirmed":int(row["confirmed"] or 0),"declined":int(row["declined"] or 0),"pending":int(row["pending"] or 0),"checked_in":checked,"attendance_percent":round(checked*100/invited,2) if invited else 0}


def send_due_reminders():
    """Scheduled worker: send one reminder per non-declined guest near 24h pre-event."""
    sent=0
    with get_db_cursor() as (cur,_):
        cur.execute("""SELECT a.id attendee_id,a.event_id,a.name,a.email,a.phone,a.rsvp_token,e.name event_name,e.event_date,e.start_time
        FROM attendees a JOIN events e ON e.id=a.event_id
        WHERE a.invitation_status<>'declined' AND TIMESTAMP(e.event_date,e.start_time)>=DATE_ADD(NOW(),INTERVAL 23 HOUR)
          AND TIMESTAMP(e.event_date,e.start_time)<=DATE_ADD(NOW(),INTERVAL 25 HOUR)
          AND NOT EXISTS(SELECT 1 FROM event_reminders er WHERE er.event_id=e.id AND er.attendee_id=a.id)""")
        for guest in cur.fetchall():
            cur.execute("INSERT IGNORE INTO event_reminders(event_id,attendee_id) VALUES(%s,%s)",(guest["event_id"],guest["attendee_id"]))
            if not cur.rowcount: continue
            link=f"{Config.PUBLIC_BASE_URL.rstrip('/')}/rsvp/{guest['rsvp_token']}" if guest["rsvp_token"] else None
            cur.execute("SELECT id FROM users WHERE email=%s",(guest["email"],)); account=cur.fetchone()
            notify_in_transaction(cur,account["id"] if account else None,f"Reminder: {guest['event_name']} is tomorrow at {guest['start_time']}.",event_type="reminder",link=link,email_to=guest["email"],phone=guest["phone"],subject=f"Reminder: {guest['event_name']} is tomorrow")
            cur.execute("INSERT INTO audit_logs(user_id,action,entity,entity_id,result) VALUES(NULL,'EVENT_REMINDER_SENT','attendees',%s,'success')",(guest["attendee_id"],)); sent+=1
    return sent
