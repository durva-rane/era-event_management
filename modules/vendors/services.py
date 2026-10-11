"""Vendor catalog, availability, booking workflow, reviews and event chat."""
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from core.config import Config
from core.db import get_db_cursor
from core.errors import AuthorizationError, ConflictError, NotFoundError, ValidationError
from modules.bookings.lifecycle_service import confirmed_booking_changed, refund_booking_in_cursor, refresh_budget_alerts
from core.notification_service import notify_in_transaction
from core.pagination import page_args


def _audit(cur,user_id,action,entity,entity_id):
    cur.execute("INSERT INTO audit_logs(user_id,action,entity,entity_id,result) VALUES(%s,%s,%s,%s,'success')",(user_id,action,entity,entity_id))


def _notify(cur,user_id,message):
    notify_in_transaction(cur,user_id,message)


def _clock(value,label):
    try: return time.fromisoformat(str(value)).strftime("%H:%M:%S")
    except (TypeError,ValueError): raise ValidationError(f"{label} must use HH:MM format.")


def _event(cur,event_id):
    cur.execute("SELECT * FROM events WHERE id=%s FOR UPDATE",(event_id,)); row=cur.fetchone()
    if not row: raise NotFoundError("Event not found.")
    return row


def _event_access(event,user_id,role):
    if role=="admin": return
    if role=="client" and event["owner_id"]==user_id: return
    if role=="organizer" and event["organizer_id"]==user_id: return
    raise AuthorizationError("You are not a client or assigned organizer for this event.")


def _commission_amount(amount):
    return (Decimal(str(amount))*Decimal(str(Config.ERA_COMMISSION_PERCENT))/Decimal(100)).quantize(Decimal("0.01"),rounding=ROUND_HALF_UP)


def save_profile(user_id,data):
    fields=[str(data.get(key,"")).strip() for key in ("business_name","service_type")]
    if not all(fields): raise ValidationError("Business name and service type are required.")
    try: price=Decimal(str(data.get("pricing",0)))
    except InvalidOperation: raise ValidationError("Pricing must be a number.")
    if price<0: raise ValidationError("Pricing cannot be negative.")
    with get_db_cursor() as (cur,_):
        cur.execute("SELECT user_id FROM vendors WHERE user_id=%s FOR UPDATE",(user_id,))
        if not cur.fetchone(): raise NotFoundError("Vendor profile not found.")
        cur.execute("UPDATE vendors SET business_name=%s,service_type=%s,description=%s,pricing=%s,location=%s WHERE user_id=%s",(fields[0],fields[1],data.get("description"),price,data.get("location"),user_id))
        _audit(cur,user_id,"VENDOR_PROFILE_UPDATED","vendors",user_id)
        _notify(cur,user_id,"Your vendor profile was updated.")


def vendor_profile(vendor_id):
    with get_db_cursor() as (cur,_):
        cur.execute("""SELECT v.user_id,v.business_name,v.service_type,v.description,v.pricing,v.location,v.verification_status,
        (v.verification_status='verified') AS verified_badge,COALESCE(AVG(r.rating),0) AS average_rating,COUNT(r.id) AS review_count
        FROM vendors v LEFT JOIN reviews r ON r.vendor_id=v.user_id WHERE v.user_id=%s GROUP BY v.user_id""",(vendor_id,))
        result=cur.fetchone()
        if not result: raise NotFoundError("Vendor not found.")
        return result


def _service_data(data):
    title=str(data.get("name","")).strip()
    try: price=Decimal(str(data.get("price","")))
    except InvalidOperation: raise ValidationError("Service price must be a number.")
    if not title or price<0: raise ValidationError("Service name and nonnegative price are required.")
    return title,price,data.get("description")


def service_action(user_id,service_id,data=None,delete=False):
    with get_db_cursor() as (cur,_):
        if service_id:
            cur.execute("SELECT vendor_id FROM vendor_services WHERE id=%s FOR UPDATE",(service_id,)); row=cur.fetchone()
            if not row: raise NotFoundError("Service not found.")
            if row["vendor_id"]!=user_id: raise AuthorizationError("You cannot manage this service.")
            if delete: cur.execute("DELETE FROM vendor_services WHERE id=%s",(service_id,)); action="VENDOR_SERVICE_DELETED"
            else:
                title,price,description=_service_data(data or {})
                cur.execute("UPDATE vendor_services SET name=%s,price=%s,description=%s WHERE id=%s",(title,price,description,service_id)); action="VENDOR_SERVICE_UPDATED"
            target=service_id
        else:
            title,price,description=_service_data(data or {})
            cur.execute("INSERT INTO vendor_services(vendor_id,name,price,description) VALUES(%s,%s,%s,%s)",(user_id,title,price,description)); target=cur.lastrowid; action="VENDOR_SERVICE_CREATED"
        _audit(cur,user_id,action,"vendor_services",target); _notify(cur,user_id,"Your service catalog was updated.")
        return target


def list_services(vendor_id, filters=None):
    page,size,offset=page_args(filters or {})
    with get_db_cursor() as (cur,_): cur.execute("SELECT * FROM vendor_services WHERE vendor_id=%s ORDER BY name LIMIT %s OFFSET %s",(vendor_id,size,offset)); return cur.fetchall()


def availability_action(user_id,slot_id,data=None,delete=False):
    data=data or {}
    try: day=date.fromisoformat(str(data.get("date")))
    except (TypeError,ValueError): day=None
    if not delete and not day: raise ValidationError("Availability date is required.")
    start=_clock(data.get("start_time"),"Start time") if not delete else None
    end=_clock(data.get("end_time"),"End time") if not delete else None
    if not delete and start>=end: raise ValidationError("End time must follow start time.")
    with get_db_cursor() as (cur,_):
        cur.execute("SELECT user_id FROM vendors WHERE user_id=%s",(user_id,))
        if not cur.fetchone(): raise NotFoundError("Vendor profile not found.")
        if slot_id:
            cur.execute("SELECT vendor_id FROM vendor_availability WHERE id=%s FOR UPDATE",(slot_id,)); row=cur.fetchone()
            if not row: raise NotFoundError("Availability slot not found.")
            if row["vendor_id"]!=user_id: raise AuthorizationError("You cannot edit this availability slot.")
        if delete: cur.execute("DELETE FROM vendor_availability WHERE id=%s",(slot_id,)); action="VENDOR_AVAILABILITY_DELETED"
        else:
            cur.execute("SELECT id FROM vendor_availability WHERE vendor_id=%s AND date=%s AND id<>%s AND start_time<%s AND end_time>%s FOR UPDATE",(user_id,day,slot_id or 0,end,start))
            if cur.fetchone(): raise ConflictError("Availability slots cannot overlap.")
            if slot_id: cur.execute("UPDATE vendor_availability SET date=%s,start_time=%s,end_time=%s WHERE id=%s",(day,start,end,slot_id)); action="VENDOR_AVAILABILITY_UPDATED"
            else: cur.execute("INSERT INTO vendor_availability(vendor_id,date,start_time,end_time) VALUES(%s,%s,%s,%s)",(user_id,day,start,end)); slot_id=cur.lastrowid; action="VENDOR_AVAILABILITY_CREATED"
        _audit(cur,user_id,action,"vendor_availability",slot_id or 0); _notify(cur,user_id,"Your vendor availability was updated.")
        return slot_id


def list_availability(vendor_id, filters=None):
    page,size,offset=page_args(filters or {})
    with get_db_cursor() as (cur,_): cur.execute("SELECT * FROM vendor_availability WHERE vendor_id=%s ORDER BY date,start_time LIMIT %s OFFSET %s",(vendor_id,size,offset)); return cur.fetchall()


def browse_vendors(filters):
    sql="""SELECT v.user_id,v.business_name,v.service_type,v.description,v.pricing,v.location,v.verification_status,
      (v.verification_status='verified') AS verified_badge,COALESCE(AVG(r.rating),0) AS average_rating,COUNT(DISTINCT r.id) AS review_count,
      MIN(s.price) AS min_service_price,MAX(s.price) AS max_service_price
      FROM vendors v LEFT JOIN reviews r ON r.vendor_id=v.user_id LEFT JOIN vendor_services s ON s.vendor_id=v.user_id
      WHERE v.verification_status='verified'"""
    args=[]
    try:
        minimum_price=Decimal(str(filters["min_price"])) if filters.get("min_price") else None
        maximum_price=Decimal(str(filters["max_price"])) if filters.get("max_price") else None
        minimum_rating=float(filters["min_rating"]) if filters.get("min_rating") else None
    except (InvalidOperation,ValueError): raise ValidationError("Price and rating filters must be numeric.")
    for key,col in (("category","v.service_type"),("service_type","v.service_type"),("location","v.location")):
        if filters.get(key): sql+=f" AND {col} LIKE %s"; args.append("%"+filters[key]+"%")
    if maximum_price is not None: sql+=" AND COALESCE(s.price,v.pricing)<=%s"; args.append(maximum_price)
    if minimum_price is not None: sql+=" AND COALESCE(s.price,v.pricing)>=%s"; args.append(minimum_price)
    if minimum_rating is not None: sql+=" AND EXISTS(SELECT 1 FROM reviews rr WHERE rr.vendor_id=v.user_id GROUP BY rr.vendor_id HAVING AVG(rr.rating)>=%s)"; args.append(minimum_rating)
    if filters.get("date") and filters.get("start_time") and filters.get("end_time"):
        start,end=_clock(filters["start_time"],"Start time"),_clock(filters["end_time"],"End time")
        sql+=" AND EXISTS(SELECT 1 FROM vendor_availability va WHERE va.vendor_id=v.user_id AND va.date=%s AND va.start_time<=%s AND va.end_time>=%s)"
        args.extend((filters["date"],start,end))
        sql+=" AND NOT EXISTS(SELECT 1 FROM bookings b WHERE b.vendor_id=v.user_id AND b.booking_type='vendor' AND b.booking_date=%s AND b.status='confirmed' AND b.start_time<%s AND b.end_time>%s)"
        args.extend((filters["date"],end,start))
    sql+=" GROUP BY v.user_id"
    page,size,offset=page_args(filters)
    sql+=" ORDER BY average_rating DESC, v.business_name LIMIT %s OFFSET %s"; args.extend((size,offset))
    with get_db_cursor() as (cur,_):
        cur.execute(sql,tuple(args)); return cur.fetchall()


def compare_vendors(ids):
    try: ids=list(dict.fromkeys(int(value) for value in ids))
    except (TypeError,ValueError): raise ValidationError("Vendor ids must be integers.")
    if not 2<=len(ids)<=4: raise ValidationError("Compare between two and four vendors.")
    placeholders=",".join(["%s"]*len(ids))
    with get_db_cursor() as (cur,_):
        cur.execute(f"""SELECT v.user_id,v.business_name,v.service_type,v.description,v.pricing,v.location,v.verification_status,
        (v.verification_status='verified') AS verified_badge,COALESCE(AVG(r.rating),0) AS average_rating,COUNT(DISTINCT r.id) AS review_count,
        GROUP_CONCAT(DISTINCT CONCAT(s.name,' (',s.price,')') ORDER BY s.name SEPARATOR ', ') AS services
        FROM vendors v LEFT JOIN reviews r ON r.vendor_id=v.user_id LEFT JOIN vendor_services s ON s.vendor_id=v.user_id
        WHERE v.user_id IN ({placeholders}) AND v.verification_status='verified' GROUP BY v.user_id""",tuple(ids))
        return cur.fetchall()


def create_booking(user_id,role,event_id,data):
    try: event_id=int(event_id)
    except (TypeError,ValueError): raise ValidationError("Event id is required.")
    try: vendor_id=int(data["vendor_id"]); service_id=int(data["service_id"])
    except (KeyError,TypeError,ValueError): raise ValidationError("Vendor and service are required.")
    try: quantity=int(data.get("quantity",1))
    except (TypeError,ValueError): raise ValidationError("Quantity must be a positive whole number.")
    if quantity<1: raise ValidationError("Quantity must be a positive whole number.")
    with get_db_cursor() as (cur,_):
        event=_event(cur,event_id); _event_access(event,user_id,role)
        day=date.fromisoformat(str(data.get("booking_date") or event["event_date"]))
        start=_clock(data.get("start_time") or event["start_time"],"Start time"); end=_clock(data.get("end_time") or event["end_time"],"End time")
        if start>=end: raise ValidationError("End time must follow start time.")
        cur.execute("SELECT v.user_id,v.verification_status,v.service_type,s.price,s.name FROM vendors v JOIN vendor_services s ON s.vendor_id=v.user_id WHERE v.user_id=%s AND s.id=%s",(vendor_id,service_id)); vendor=cur.fetchone()
        if not vendor: raise NotFoundError("Vendor service not found.")
        if vendor["verification_status"]!="verified": raise ConflictError("Only verified vendors can be booked.")
        amount=Decimal(str(vendor["price"]))*quantity
        cur.execute("INSERT INTO bookings(event_id,booking_type,vendor_id,service_id,booking_date,start_time,end_time,quantity,budget_category,amount,status) VALUES(%s,'vendor',%s,%s,%s,%s,%s,%s,%s,%s,'requested')",(event_id,vendor_id,service_id,day,start,end,quantity,vendor["service_type"],amount))
        booking_id=cur.lastrowid
        recipient=vendor_id
        _notify(cur,recipient,f"New booking request for '{event['name']}' ({day} {start}-{end}).")
        _audit(cur,user_id,"VENDOR_BOOKING_REQUESTED","bookings",booking_id)
        return booking_id


def respond_booking(vendor_id,booking_id,decision):
    if decision not in ("accepted","rejected"): raise ValidationError("Decision must be accepted or rejected.")
    with get_db_cursor() as (cur,_):
        cur.execute("SELECT b.*,e.owner_id,e.organizer_id,e.name AS event_name FROM bookings b JOIN events e ON e.id=b.event_id WHERE b.id=%s AND b.booking_type='vendor' FOR UPDATE",(booking_id,)); booking=cur.fetchone()
        if not booking: raise NotFoundError("Vendor booking request not found.")
        if booking["vendor_id"]!=vendor_id: raise AuthorizationError("You cannot respond to this request.")
        if booking["status"]!="requested": raise ConflictError("This request has already been answered.")
        if decision=="accepted":
            cur.execute("SELECT id FROM vendors WHERE user_id=%s AND verification_status='verified' FOR UPDATE",(vendor_id,))
            if not cur.fetchone(): raise ConflictError("Only verified vendors can accept bookings.")
            cur.execute("SELECT id FROM vendor_availability WHERE vendor_id=%s AND date=%s AND start_time<=%s AND end_time>=%s FOR UPDATE",(vendor_id,booking["booking_date"],booking["start_time"],booking["end_time"]))
            if not cur.fetchone(): raise ConflictError("The requested time is outside your availability slots.")
            cur.execute("SELECT id FROM bookings WHERE vendor_id=%s AND booking_type='vendor' AND booking_date=%s AND status='confirmed' AND start_time<%s AND end_time>%s FOR UPDATE",(vendor_id,booking["booking_date"],booking["end_time"],booking["start_time"]))
            if cur.fetchone(): raise ConflictError("The requested time overlaps another confirmed booking.")
            commission=_commission_amount(booking["amount"])
            status="confirmed"
            cur.execute("UPDATE bookings SET status=%s,commission_amount=%s WHERE id=%s",(status,commission,booking_id))
            confirmed_booking_changed(cur,booking_id,vendor_id)
        else:
            status="rejected"; cur.execute("UPDATE bookings SET status=%s WHERE id=%s",(status,booking_id))
        _notify(cur,booking["owner_id"],f"Vendor {status} the booking for '{booking['event_name']}'.")
        if booking["organizer_id"] and booking["organizer_id"]!=booking["owner_id"]: _notify(cur,booking["organizer_id"],f"Vendor {status} the booking for '{booking['event_name']}'.")
        _notify(cur,vendor_id,f"Booking request #{booking_id} was {status}.")
        _audit(cur,vendor_id,f"VENDOR_BOOKING_{status.upper()}","bookings",booking_id)
        return {"booking_id":booking_id,"status":status,"commission_amount":commission if decision=="accepted" else Decimal("0.00")}


def vendor_requests(vendor_id, filters=None):
    page,size,offset=page_args(filters or {})
    with get_db_cursor() as (cur,_):
        cur.execute("""SELECT b.*,e.name AS event_name,e.category,e.expected_attendees,u.name AS requester_name,vs.name AS service_name
        FROM bookings b JOIN events e ON e.id=b.event_id JOIN users u ON u.id=e.owner_id LEFT JOIN vendor_services vs ON vs.id=b.service_id
        WHERE b.vendor_id=%s AND b.booking_type='vendor' AND b.status='requested' ORDER BY b.booking_date,b.start_time LIMIT %s OFFSET %s""",(vendor_id,size,offset)); return cur.fetchall()


def list_bookings(user_id,role,filters=None):
    sql="""SELECT b.*,e.name AS event_name,v.business_name AS vendor_name,vs.name AS service_name
      FROM bookings b JOIN events e ON e.id=b.event_id LEFT JOIN vendors v ON v.user_id=b.vendor_id LEFT JOIN vendor_services vs ON vs.id=b.service_id
      WHERE b.booking_type='vendor'"""
    args=[]
    if role=="vendor": sql+=" AND b.vendor_id=%s"; args.append(user_id)
    elif role=="client": sql+=" AND e.owner_id=%s"; args.append(user_id)
    elif role=="organizer": sql+=" AND e.organizer_id=%s"; args.append(user_id)
    elif role!="admin": return []
    page,size,offset=page_args(filters or {})
    sql+=" ORDER BY b.booking_date DESC,b.start_time LIMIT %s OFFSET %s"; args.extend((size,offset))
    with get_db_cursor() as (cur,_): cur.execute(sql,tuple(args)); return cur.fetchall()


def cancel_booking(user_id,role,booking_id,reason):
    if not str(reason or "").strip(): raise ValidationError("A cancellation reason is required.")
    with get_db_cursor() as (cur,_):
        cur.execute("SELECT b.*,e.owner_id,e.organizer_id,e.event_date,e.name AS event_name FROM bookings b JOIN events e ON e.id=b.event_id WHERE b.id=%s AND b.booking_type='vendor' FOR UPDATE",(booking_id,)); booking=cur.fetchone()
        if not booking: raise NotFoundError("Vendor booking not found.")
        allowed=(role=="vendor" and user_id==booking["vendor_id"]) or (role=="client" and user_id==booking["owner_id"]) or (role=="organizer" and user_id==booking["organizer_id"])
        if not allowed: raise AuthorizationError("You cannot cancel this booking.")
        if booking["status"] not in ("requested","confirmed"): raise ConflictError("Only requested or confirmed bookings can be cancelled.")
        end_value=booking["end_time"]
        if isinstance(end_value,time): end_clock=end_value
        else: end_clock=(datetime.min+end_value).time()
        if booking["status"]=="confirmed" and (booking["booking_date"]<date.today() or (booking["booking_date"]==date.today() and end_clock<=datetime.now().time())): raise ConflictError("A booking cannot be cancelled after its event slot ends.")
        refund_booking_in_cursor(cur,booking_id,user_id)
        cur.execute("UPDATE bookings SET status='cancelled',cancelled_by=%s,cancellation_reason=%s,cancelled_at=NOW() WHERE id=%s",(user_id,str(reason).strip(),booking_id))
        refresh_budget_alerts(cur,booking["event_id"],user_id)
        others={booking["vendor_id"],booking["owner_id"],booking["organizer_id"]}-{None,user_id}
        for target in others: _notify(cur,target,f"Booking for '{booking['event_name']}' was cancelled. Reason: {reason.strip()}")
        _notify(cur,user_id,f"Booking #{booking_id} was cancelled.")
        _audit(cur,user_id,"VENDOR_BOOKING_CANCELLED","bookings",booking_id)


def complete_booking(vendor_id,booking_id):
    with get_db_cursor() as (cur,_):
        cur.execute("SELECT b.*,e.owner_id,e.organizer_id,e.name AS event_name FROM bookings b JOIN events e ON e.id=b.event_id WHERE b.id=%s AND b.booking_type='vendor' FOR UPDATE",(booking_id,)); booking=cur.fetchone()
        if not booking: raise NotFoundError("Vendor booking not found.")
        if booking["vendor_id"]!=vendor_id: raise AuthorizationError("You cannot complete this booking.")
        if booking["status"]!="confirmed": raise ConflictError("Only confirmed bookings can be completed.")
        cur.execute("UPDATE bookings SET status='completed' WHERE id=%s",(booking_id,))
        _notify(cur,booking["owner_id"],f"Vendor marked '{booking['event_name']}' booking complete. You can now leave a review.")
        _audit(cur,vendor_id,"VENDOR_BOOKING_COMPLETED","bookings",booking_id)


def create_review(user_id,role,booking_id,data):
    try: rating=int(data.get("rating"))
    except (TypeError,ValueError): raise ValidationError("Rating must be from 1 to 5.")
    if not 1<=rating<=5: raise ValidationError("Rating must be from 1 to 5.")
    with get_db_cursor() as (cur,_):
        cur.execute("SELECT b.*,e.owner_id,e.organizer_id,e.name AS event_name FROM bookings b JOIN events e ON e.id=b.event_id WHERE b.id=%s AND b.booking_type='vendor' FOR UPDATE",(booking_id,)); booking=cur.fetchone()
        if not booking: raise NotFoundError("Vendor booking not found.")
        if booking["status"]!="completed": raise ConflictError("Reviews are allowed only after a completed booking.")
        if not ((role=="client" and user_id==booking["owner_id"]) or (role=="organizer" and user_id==booking["organizer_id"])): raise AuthorizationError("Only the event client or assigned organizer can review this booking.")
        cur.execute("SELECT id FROM reviews WHERE booking_id=%s AND reviewer_id=%s",(booking_id,user_id))
        if cur.fetchone(): raise ConflictError("You have already reviewed this booking.")
        cur.execute("INSERT INTO reviews(booking_id,reviewer_id,vendor_id,rating,comment) VALUES(%s,%s,%s,%s,%s)",(booking_id,user_id,booking["vendor_id"],rating,data.get("comment")))
        review_id=cur.lastrowid
        _notify(cur,booking["vendor_id"],f"You received a {rating}-star review for '{booking['event_name']}'.")
        _audit(cur,user_id,"VENDOR_REVIEW_CREATED","reviews",review_id)
        return review_id


def event_messages(user_id,role,event_id,after_id=0,message=None):
    with get_db_cursor() as (cur,_):
        event=_event(cur,event_id); _event_access(event,user_id,role)
        peer=event["organizer_id"] if user_id==event["owner_id"] else event["owner_id"]
        if not peer: raise ConflictError("This event has no assigned organizer yet.")
        if message is not None:
            message=str(message).strip()
            if not message or len(message)>4000: raise ValidationError("Message must contain 1 to 4000 characters.")
            cur.execute("INSERT INTO chat_messages(event_id,sender_id,receiver_id,message) VALUES(%s,%s,%s,%s)",(event_id,user_id,peer,message)); message_id=cur.lastrowid
            _notify(cur,peer,f"New message about '{event['name']}'."); _audit(cur,user_id,"EVENT_MESSAGE_SENT","chat_messages",message_id)
        cur.execute("SELECT c.id,c.event_id,c.sender_id,c.receiver_id,c.message,c.sent_at,u.name AS sender_name FROM chat_messages c JOIN users u ON u.id=c.sender_id WHERE c.event_id=%s AND c.id>%s ORDER BY c.id LIMIT 200",(event_id,int(after_id or 0)))
        return cur.fetchall()
