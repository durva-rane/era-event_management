"""Per-role dashboard data from SQL aggregates and bounded recent-row queries."""
from core.db import get_db_cursor


def _client_organizer(user_id, role):
    owner_field = "owner_id" if role == "client" else "organizer_id"
    with get_db_cursor(commit_on_success=False) as (cur, _):
        cur.execute(f"""SELECT COUNT(*) total_events,SUM(e.event_date>=CURRENT_DATE AND e.status NOT IN ('cancelled','completed')) upcoming_events,
          COALESCE(SUM(COALESCE(NULLIF(bg.total_amount,0),bi.allocated,0)),0) allocated,
          COALESCE(SUM(COALESCE(bt.confirmed,0)+COALESCE(py.paid,0)),0) spent,
          (SELECT COUNT(*) FROM bookings bx JOIN events ex ON ex.id=bx.event_id WHERE ex.{owner_field}=%s) booking_count
          FROM events e LEFT JOIN budgets bg ON bg.event_id=e.id
          LEFT JOIN (SELECT budget_id,SUM(allocated_amount) allocated FROM budget_items GROUP BY budget_id) bi ON bi.budget_id=bg.id
          LEFT JOIN (SELECT event_id,SUM(CASE WHEN status='confirmed' THEN amount ELSE 0 END) confirmed FROM bookings GROUP BY event_id) bt ON bt.event_id=e.id
          LEFT JOIN (SELECT b.event_id,SUM(CASE WHEN p.record_type='charge' AND p.status IN ('success','refunded') THEN p.amount WHEN p.record_type='refund' AND p.status='success' THEN -p.amount ELSE 0 END) paid
            FROM payments p JOIN bookings b ON b.id=p.booking_id GROUP BY b.event_id) py ON py.event_id=e.id
          WHERE e.{owner_field}=%s""", (user_id, user_id))
        metrics = cur.fetchone()
        cur.execute(f"""SELECT b.id,b.booking_date,b.amount,b.status,b.payment_status,e.name event_name,
          COALESCE(v.business_name,ve.name,'Delivery') counterparty
          FROM bookings b JOIN events e ON e.id=b.event_id LEFT JOIN vendors v ON v.user_id=b.vendor_id LEFT JOIN venues ve ON ve.id=b.venue_id
          WHERE e.{owner_field}=%s ORDER BY b.created_at DESC,b.id DESC LIMIT 8""", (user_id,))
        recent = cur.fetchall()
        cur.execute(f"SELECT id,name,event_date,status FROM events WHERE {owner_field}=%s AND event_date>=CURRENT_DATE AND status NOT IN ('cancelled','completed') ORDER BY event_date LIMIT 6", (user_id,))
        upcoming = cur.fetchall()
        return {"metrics": metrics, "recent": recent, "upcoming": upcoming}


def _vendor(user_id):
    with get_db_cursor(commit_on_success=False) as (cur, _):
        cur.execute("""SELECT SUM(status='requested') requests,COUNT(*) total_bookings,
          COALESCE(SUM(CASE WHEN status IN ('confirmed','completed') THEN amount-commission_amount ELSE 0 END),0) earnings
          FROM bookings WHERE booking_type='vendor' AND vendor_id=%s""", (user_id,))
        metrics = cur.fetchone()
        cur.execute("""SELECT b.id,b.booking_date,b.start_time,b.end_time,b.amount,b.status,e.name event_name,vs.name service_name
          FROM bookings b JOIN events e ON e.id=b.event_id LEFT JOIN vendor_services vs ON vs.id=b.service_id
          WHERE b.vendor_id=%s AND b.status IN ('requested','confirmed') ORDER BY b.booking_date,b.start_time LIMIT 10""", (user_id,))
        schedule = cur.fetchall()
        return {"metrics": metrics, "schedule": schedule}


def _venue_owner(user_id):
    with get_db_cursor(commit_on_success=False) as (cur, _):
        cur.execute("""SELECT COUNT(b.id) total_bookings,SUM(b.status='requested') requests,
          SUM(b.status='confirmed' AND b.booking_date>=CURRENT_DATE) upcoming,
          COALESCE(SUM(CASE WHEN b.status IN ('confirmed','completed') THEN b.amount ELSE 0 END),0) revenue
          FROM venues v LEFT JOIN bookings b ON b.venue_id=v.id WHERE v.owner_id=%s""", (user_id,))
        metrics = cur.fetchone()
        cur.execute("""SELECT b.id,b.booking_date,b.start_time,b.end_time,b.status,b.amount,e.name event_name,v.name venue_name
          FROM bookings b JOIN venues v ON v.id=b.venue_id JOIN events e ON e.id=b.event_id
          WHERE v.owner_id=%s ORDER BY b.booking_date DESC,b.id DESC LIMIT 10""", (user_id,))
        recent = cur.fetchall()
        return {"metrics": metrics, "recent": recent}


def _attendee(email):
    with get_db_cursor(commit_on_success=False) as (cur, _):
        cur.execute("""SELECT COUNT(*) invitations,SUM(a.rsvp_status='accepted') confirmed,SUM(a.rsvp_status='declined') declined,
          SUM(a.rsvp_status IN ('pending','maybe')) pending FROM attendees a WHERE LOWER(a.email)=LOWER(%s)""", (email,))
        metrics = cur.fetchone()
        cur.execute("""SELECT e.id event_id,e.name event_name,e.event_date,e.start_time,e.end_time,a.rsvp_status,a.invitation_status,
          COALESCE(v.name,'Venue to be announced') venue_name FROM attendees a JOIN events e ON e.id=a.event_id
          LEFT JOIN venues v ON v.id=e.venue_id WHERE LOWER(a.email)=LOWER(%s) ORDER BY e.event_date LIMIT 10""", (email,))
        invitations = cur.fetchall()
        return {"metrics": metrics, "invitations": invitations}


def _delivery(partner_id):
    with get_db_cursor(commit_on_success=False) as (cur, _):
        cur.execute("""SELECT COUNT(*) total_tasks,SUM(status IN ('assigned','accepted','pickup_pending','picked_up','in_transit')) active_tasks,
          SUM(status='delivered') delivered,SUM(status='failed') failed FROM delivery_tasks WHERE partner_id=%s""", (partner_id,))
        metrics = cur.fetchone()
        cur.execute("""SELECT t.id,t.scheduled_at,t.pickup,t.destination,t.item_description,t.quantity,t.status,e.name event_name
          FROM delivery_tasks t JOIN events e ON e.id=t.event_id WHERE t.partner_id=%s
          ORDER BY (t.status IN ('delivered','failed','cancelled','rejected')),t.scheduled_at DESC LIMIT 10""", (partner_id,))
        tasks = cur.fetchall()
        return {"metrics": metrics, "tasks": tasks}


def _admin():
    with get_db_cursor(commit_on_success=False) as (cur, _):
        cur.execute("""SELECT (SELECT COUNT(*) FROM users) users,(SELECT COUNT(*) FROM events) events,
          (SELECT COUNT(*) FROM events WHERE event_date>=CURRENT_DATE AND status NOT IN ('cancelled','completed')) upcoming_events,
          (SELECT COUNT(*) FROM bookings) bookings,(SELECT COUNT(*) FROM bookings WHERE status='requested') requests,
          (SELECT COALESCE(SUM(commission_amount),0) FROM bookings WHERE status IN ('confirmed','completed')) commission,
          (SELECT COUNT(*) FROM venues WHERE status='pending') pending_venues,
          (SELECT COUNT(*) FROM vendors WHERE verification_status='pending') pending_vendors""")
        metrics = cur.fetchone()
        cur.execute("SELECT id,action,entity,created_at FROM audit_logs ORDER BY created_at DESC,id DESC LIMIT 10")
        activity = cur.fetchall()
        return {"metrics": metrics, "activity": activity}


def dashboard(user_id, role, email):
    if role in ("client", "organizer"): return _client_organizer(user_id, role)
    if role == "vendor": return _vendor(user_id)
    if role == "venue_owner": return _venue_owner(user_id)
    if role == "attendee": return _attendee(email)
    if role == "delivery_partner": return _delivery(user_id)
    if role == "admin": return _admin()
    return {"metrics": {}, "recent": []}
