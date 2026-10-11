"""Role-scoped operational reports. All report rollups are performed in SQL."""
import csv
from datetime import date
from io import StringIO

from core.db import get_db_cursor
from core.errors import AuthorizationError, ValidationError
from core.pagination import page_args

REPORTS = {
    "events": "Events",
    "attendance": "Attendance",
    "budget": "Budget",
    "bookings": "Booking history",
    "platform": "Platform overview",
}
ROLE_REPORTS = {
    "client": ("events", "attendance", "budget", "bookings"),
    "organizer": ("events", "attendance", "budget", "bookings"),
    "vendor": ("bookings",),
    "venue_owner": ("bookings",),
    "attendee": ("attendance",),
    "admin": tuple(REPORTS),
}


def _filters(args):
    values = {key: str(args.get(key, "")).strip() or None for key in ("from", "to", "event_id", "vendor_id", "status")}
    for key in ("from", "to"):
        if values[key]:
            try: date.fromisoformat(values[key])
            except ValueError: raise ValidationError(f"{key.title()} date must use YYYY-MM-DD.")
    if values["from"] and values["to"] and values["from"] > values["to"]:
        raise ValidationError("From date must be on or before the to date.")
    for key in ("event_id", "vendor_id"):
        if values[key]:
            try: values[key] = int(values[key])
            except ValueError: raise ValidationError(f"{key.replace('_',' ').title()} must be an integer.")
    return values


def allowed_reports(role):
    return ROLE_REPORTS.get(role, ())


def filter_events(user_id, role, filters=None):
    sql = "SELECT e.id,e.name FROM events e WHERE 1=1"
    params = []
    if role == "client": sql += " AND e.owner_id=%s"; params.append(user_id)
    elif role == "organizer": sql += " AND e.organizer_id=%s"; params.append(user_id)
    elif role == "vendor": sql += " AND EXISTS(SELECT 1 FROM bookings b WHERE b.event_id=e.id AND b.vendor_id=%s)"; params.append(user_id)
    elif role == "venue_owner": sql += " AND EXISTS(SELECT 1 FROM bookings b JOIN venues v ON v.id=b.venue_id WHERE b.event_id=e.id AND v.owner_id=%s)"; params.append(user_id)
    elif role == "attendee": sql += " AND EXISTS(SELECT 1 FROM attendees a JOIN users u ON LOWER(u.email)=LOWER(a.email) WHERE a.event_id=e.id AND u.id=%s)"; params.append(user_id)
    elif role != "admin": return []
    page,size,offset=page_args(filters or {})
    sql += " ORDER BY e.event_date DESC,e.id DESC LIMIT %s OFFSET %s"; params.extend((size,offset))
    with get_db_cursor(commit_on_success=False) as (cur, _): cur.execute(sql, tuple(params)); return cur.fetchall()


def filter_vendors(user_id, role, filters=None):
    sql = "SELECT DISTINCT v.user_id,v.business_name FROM vendors v JOIN bookings b ON b.vendor_id=v.user_id JOIN events e ON e.id=b.event_id WHERE 1=1"
    params = []
    if role == "client": sql += " AND e.owner_id=%s"; params.append(user_id)
    elif role == "organizer": sql += " AND e.organizer_id=%s"; params.append(user_id)
    elif role != "admin": return []
    page,size,offset=page_args(filters or {})
    sql += " ORDER BY v.business_name LIMIT %s OFFSET %s"; params.extend((size,offset))
    with get_db_cursor(commit_on_success=False) as (cur, _): cur.execute(sql, tuple(params)); return cur.fetchall()


def _where_events(role, user_id, f, alias="e"):
    sql, params = [], []
    if role == "client": sql.append(f"{alias}.owner_id=%s"); params.append(user_id)
    elif role == "organizer": sql.append(f"{alias}.organizer_id=%s"); params.append(user_id)
    elif role == "vendor": sql.append(f"EXISTS(SELECT 1 FROM bookings sx WHERE sx.event_id={alias}.id AND sx.vendor_id=%s)"); params.append(user_id)
    elif role == "venue_owner": sql.append(f"EXISTS(SELECT 1 FROM bookings sx JOIN venues sv ON sv.id=sx.venue_id WHERE sx.event_id={alias}.id AND sv.owner_id=%s)"); params.append(user_id)
    elif role == "attendee": sql.append(f"EXISTS(SELECT 1 FROM attendees sa JOIN users su ON LOWER(su.email)=LOWER(sa.email) WHERE sa.event_id={alias}.id AND su.id=%s)"); params.append(user_id)
    elif role != "admin": raise AuthorizationError("This role cannot access reports.")
    if f["event_id"]:
        sql.append(f"{alias}.id=%s"); params.append(f["event_id"])
    return sql, params


def _date_conditions(f, column, sql, params):
    if f["from"]: sql.append(f"{column}>=%s"); params.append(f["from"])
    if f["to"]: sql.append(f"{column}<=%s"); params.append(f["to"])


def _report_events(user_id, role, f):
    where, p = _where_events(role, user_id, f)
    _date_conditions(f, "e.event_date", where, p)
    if f["status"]: where.append("e.status=%s"); p.append(f["status"])
    if f["vendor_id"]: where.append("EXISTS(SELECT 1 FROM bookings vb WHERE vb.event_id=e.id AND vb.vendor_id=%s)"); p.append(f["vendor_id"])
    sql = """SELECT e.id AS event_id,e.name AS event_name,e.category,e.event_date,e.start_time,e.end_time,e.status,
      COALESCE(v.name,'Not selected') AS venue,COALESCE(v.capacity,0) AS venue_capacity,e.expected_attendees,
      COUNT(a.id) AS invited,COALESCE(SUM(a.rsvp_status='accepted'),0) AS confirmed_attendees,COALESCE(SUM(a.checked_in_at IS NOT NULL),0) AS actual_attendees,
      ROUND(100*e.expected_attendees/NULLIF(v.capacity,0),2) AS venue_utilization_percent
      FROM events e LEFT JOIN venues v ON v.id=e.venue_id LEFT JOIN attendees a ON a.event_id=e.id"""
    if where: sql += " WHERE " + " AND ".join(where)
    sql += " GROUP BY e.id,v.id ORDER BY e.event_date DESC,e.id DESC"
    return ("events", sql, tuple(p), ["event_id","event_name","category","event_date","start_time","end_time","status","venue","venue_capacity","expected_attendees","invited","confirmed_attendees","actual_attendees","venue_utilization_percent"])


def _report_attendance(user_id, role, f):
    where, p = _where_events(role, user_id, f)
    _date_conditions(f, "e.event_date", where, p)
    if f["status"]: where.append("e.status=%s"); p.append(f["status"])
    if f["vendor_id"]: where.append("EXISTS(SELECT 1 FROM bookings vb WHERE vb.event_id=e.id AND vb.vendor_id=%s)"); p.append(f["vendor_id"])
    if role == "attendee":
        where.append("LOWER(a.email)=(SELECT LOWER(email) FROM users WHERE id=%s)"); p.append(user_id)
    sql = """SELECT e.id AS event_id,e.name AS event_name,e.event_date,COUNT(a.id) AS invited,
      COALESCE(SUM(a.rsvp_status='accepted'),0) AS confirmed,COALESCE(SUM(a.rsvp_status='declined'),0) AS declined,
      COALESCE(SUM(a.rsvp_status IN ('pending','maybe')),0) AS pending,COALESCE(SUM(a.checked_in_at IS NOT NULL),0) AS actual,
      COALESCE(ROUND(100*SUM(a.checked_in_at IS NOT NULL)/NULLIF(COUNT(a.id),0),2),0) AS attendance_percent
      FROM events e LEFT JOIN attendees a ON a.event_id=e.id"""
    if role == "attendee": sql = sql.replace("LEFT JOIN attendees a ON a.event_id=e.id", "LEFT JOIN attendees a ON a.event_id=e.id AND LOWER(a.email)=(SELECT LOWER(email) FROM users WHERE id=%s)"); p = [user_id] + p
    if where: sql += " WHERE " + " AND ".join(where)
    sql += " GROUP BY e.id ORDER BY e.event_date DESC,e.id DESC"
    return ("attendance", sql, tuple(p), ["event_id","event_name","event_date","invited","confirmed","declined","pending","actual","attendance_percent"])


def _report_budget(user_id, role, f):
    where, p = _where_events(role, user_id, f)
    _date_conditions(f, "e.event_date", where, p)
    if f["status"]: where.append("e.status=%s"); p.append(f["status"])
    if f["vendor_id"]: where.append("EXISTS(SELECT 1 FROM bookings vb WHERE vb.event_id=e.id AND vb.vendor_id=%s)"); p.append(f["vendor_id"])
    sql = """SELECT e.id AS event_id,e.name AS event_name,
      COALESCE(NULLIF(b.total_amount,0),bi.allocated,0) AS allocated,
      COALESCE(bi.estimated,0)+COALESCE(bt.estimate,0) AS estimated,
      COALESCE(bt.confirmed,0)+COALESCE(pay.paid,0) AS actual,
      COALESCE(bt.vendor_expenses,0) AS vendor_expenses,
      COALESCE(NULLIF(b.total_amount,0),bi.allocated,0)-COALESCE(bt.confirmed,0)-COALESCE(pay.paid,0) AS remaining,
      COALESCE(NULLIF(b.total_amount,0),bi.allocated,0)-COALESCE(bt.confirmed,0)-COALESCE(pay.paid,0) AS variance
      FROM events e LEFT JOIN budgets b ON b.event_id=e.id
      LEFT JOIN (SELECT budget_id,SUM(allocated_amount) allocated,SUM(estimated_amount) estimated FROM budget_items GROUP BY budget_id) bi ON bi.budget_id=b.id
      LEFT JOIN (SELECT event_id,SUM(CASE WHEN status='confirmed' THEN amount ELSE 0 END) confirmed,
        SUM(CASE WHEN status IN ('requested','confirmed') THEN amount ELSE 0 END) estimate,
        SUM(CASE WHEN status='confirmed' AND booking_type='vendor' THEN amount ELSE 0 END) vendor_expenses
        FROM bookings GROUP BY event_id) bt ON bt.event_id=e.id
      LEFT JOIN (SELECT b.event_id,SUM(CASE WHEN p.record_type='charge' AND p.status IN ('success','refunded') THEN p.amount WHEN p.record_type='refund' AND p.status='success' THEN -p.amount ELSE 0 END) paid
        FROM payments p JOIN bookings b ON b.id=p.booking_id GROUP BY b.event_id) pay ON pay.event_id=e.id"""
    if where: sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY e.event_date DESC,e.id DESC"
    return ("budget", sql, tuple(p), ["event_id","event_name","allocated","estimated","actual","vendor_expenses","remaining","variance"])


def _report_bookings(user_id, role, f):
    where, p = [], []
    if role == "client": where.append("e.owner_id=%s"); p.append(user_id)
    elif role == "organizer": where.append("e.organizer_id=%s"); p.append(user_id)
    elif role == "vendor": where.extend(["b.booking_type='vendor'", "b.vendor_id=%s"]); p.append(user_id)
    elif role == "venue_owner": where.extend(["b.booking_type='venue'", "v.owner_id=%s"]); p.append(user_id)
    elif role != "admin": raise AuthorizationError("This role cannot access booking reports.")
    if f["event_id"]: where.append("e.id=%s"); p.append(f["event_id"])
    _date_conditions(f, "b.booking_date", where, p)
    if f["status"] in ("payment_pending", "partially_paid", "paid", "refunded"):
        where.append("b.payment_status=%s"); p.append(f["status"])
    elif f["status"]: where.append("b.status=%s"); p.append(f["status"])
    if f["vendor_id"]: where.append("b.vendor_id=%s"); p.append(f["vendor_id"])
    sql = """SELECT b.id AS booking_id,e.id AS event_id,e.name AS event_name,b.booking_type,
      COALESCE(v.name,vp.business_name,'—') AS vendor_or_venue,b.booking_date,b.start_time,b.end_time,b.amount,b.status AS booking_status,
      b.payment_status,b.cancelled_at,b.cancellation_reason,COALESCE(cu.name,'') AS cancelled_by
      FROM bookings b JOIN events e ON e.id=b.event_id LEFT JOIN venues v ON v.id=b.venue_id
      LEFT JOIN vendors vp ON vp.user_id=b.vendor_id LEFT JOIN users cu ON cu.id=b.cancelled_by"""
    if where: sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY b.booking_date DESC,b.id DESC"
    return ("bookings", sql, tuple(p), ["booking_id","event_id","event_name","booking_type","vendor_or_venue","booking_date","start_time","end_time","amount","booking_status","payment_status","cancelled_at","cancellation_reason","cancelled_by"])


def _report_platform(f):
    where, p = [], []
    _date_conditions(f, "a.created_at", where, p)
    if f["status"]: where.append("a.result=%s"); p.append(f["status"])
    if f["event_id"]:
        where.append("((a.entity='events' AND a.entity_id=%s) OR (a.entity='bookings' AND a.entity_id IN (SELECT id FROM bookings WHERE event_id=%s)))")
        p.extend([f["event_id"], f["event_id"]])
    if f["vendor_id"]:
        where.append("(a.entity='bookings' AND a.entity_id IN (SELECT id FROM bookings WHERE vendor_id=%s))")
        p.append(f["vendor_id"])
    sql = "SELECT a.action,a.entity,a.result,COUNT(*) AS activity_count,MAX(a.created_at) AS last_activity FROM audit_logs a"
    if where: sql += " WHERE " + " AND ".join(where)
    sql += " GROUP BY a.action,a.entity,a.result ORDER BY activity_count DESC,a.action"
    return ("platform", sql, tuple(p), ["action","entity","result","activity_count","last_activity"])


def report(user_id, role, report_type, args):
    if report_type not in allowed_reports(role): raise AuthorizationError("This report is not available to your role.")
    f = _filters(args)
    if report_type == "events": spec = _report_events(user_id, role, f)
    elif report_type == "attendance": spec = _report_attendance(user_id, role, f)
    elif report_type == "budget": spec = _report_budget(user_id, role, f)
    elif report_type == "bookings": spec = _report_bookings(user_id, role, f)
    else: spec = _report_platform(f)
    name, sql, params, columns = spec
    page,size,offset=page_args(args)
    sql += " LIMIT %s OFFSET %s"
    params = tuple(params) + (size,offset)
    with get_db_cursor(commit_on_success=False) as (cur, _):
        cur.execute(sql, params); rows = cur.fetchall()
        if report_type == "platform":
            commission_where = ["status IN ('confirmed','completed')"]
            commission_params = []
            _date_conditions(f, "booking_date", commission_where, commission_params)
            if f["event_id"]: commission_where.append("event_id=%s"); commission_params.append(f["event_id"])
            if f["vendor_id"]: commission_where.append("vendor_id=%s"); commission_params.append(f["vendor_id"])
            cur.execute(f"""SELECT (SELECT COUNT(*) FROM users) users,(SELECT COUNT(*) FROM events) events,
              (SELECT COUNT(*) FROM bookings) bookings,(SELECT COALESCE(SUM(commission_amount),0) FROM bookings WHERE {' AND '.join(commission_where)}) commission_earned,
              (SELECT COUNT(*) FROM bookings WHERE status='requested') open_requests,
              (SELECT COUNT(*) FROM venues WHERE status='pending') pending_venues,
              (SELECT COUNT(*) FROM vendors WHERE verification_status='pending') pending_vendors""", tuple(commission_params))
            summary = cur.fetchone()
        else: summary = None
        return {"type": name, "title": REPORTS[report_type], "columns": columns, "rows": rows, "summary": summary, "filters": f, "page": page, "per_page": size}


def csv_export(result):
    output = StringIO(); writer = csv.writer(output)
    if result["summary"]:
        writer.writerow(["Platform metric", "Value"])
        writer.writerows(result["summary"].items())
        writer.writerow([])
    writer.writerow(result["columns"])
    writer.writerows([[row.get(column) for column in result["columns"]] for row in result["rows"]])
    return output.getvalue()


def pdf_export(result):
    # Lightweight multi-page text PDF, avoiding an additional runtime dependency.
    lines = [result["title"], " | ".join(result["columns"])]
    if result["summary"]:
        lines.extend(f"{key}: {value}" for key, value in result["summary"].items())
        lines.extend(["", "Activity summary"])
    lines.extend(" | ".join(str(row.get(col, "") or "") for col in result["columns"]) for row in result["rows"])
    escape = lambda value: str(value).encode("ascii", "replace").decode().replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")[:160]
    pages = [lines[index:index + 62] for index in range(0, len(lines), 62)] or [[]]
    objects = ["<< /Type /Catalog /Pages 2 0 R >>", "", "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    page_ids = []
    for page_lines in pages:
        page_id = len(objects) + 1; content_id = page_id + 1; page_ids.append(page_id)
        stream = "BT /F1 8 Tf 36 806 Td 11 TL " + " ".join(f"({escape(line)}) Tj T*" for line in page_lines) + " ET"
        objects.extend([f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>", f"<< /Length {len(stream.encode())} >>\nstream\n{stream}\nendstream"])
    objects[1] = "<< /Type /Pages /Kids [" + " ".join(f"{page_id} 0 R" for page_id in page_ids) + f"] /Count {len(page_ids)} >>"
    pdf = "%PDF-1.4\n"; offsets = [0]
    for index, obj in enumerate(objects, 1): offsets.append(len(pdf.encode())); pdf += f"{index} 0 obj\n{obj}\nendobj\n"
    xref = len(pdf.encode()); size = len(objects) + 1
    pdf += f"xref\n0 {size}\n0000000000 65535 f \n" + "".join(f"{offset:010d} 00000 n \n" for offset in offsets[1:]) + f"trailer\n<< /Size {size} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF"
    return pdf.encode()
