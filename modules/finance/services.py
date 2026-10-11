"""Budget rollups, invoice records, gateway-backed payments and refunds."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import BytesIO
import secrets

from core.config import Config
from core.db import get_db_cursor
from core.errors import AuthorizationError, ConflictError, NotFoundError, ValidationError
from modules.finance.gateways import get_gateway
from core.notification_service import notify_in_transaction


def _audit(cur,user_id,action,entity,entity_id):
    cur.execute("INSERT INTO audit_logs(user_id,action,entity,entity_id,result) VALUES(%s,%s,%s,%s,'success')",(user_id,action,entity,entity_id))


def _notify(cur,user_id,message):
    notify_in_transaction(cur,user_id,message)


def _event(cur,event_id):
    cur.execute("SELECT * FROM events WHERE id=%s FOR UPDATE",(event_id,)); event=cur.fetchone()
    if not event: raise NotFoundError("Event not found.")
    return event


def _event_access(event,user_id,role):
    if role=="admin": return
    if role=="client" and event["owner_id"]==user_id: return
    if role=="organizer" and event["organizer_id"]==user_id: return
    raise AuthorizationError("You cannot manage this event's budget or payments.")


def _booking_access(booking,user_id,role):
    if role=="admin": return
    if role=="vendor" and booking.get("vendor_id")==user_id: return
    if role=="client" and booking.get("owner_id")==user_id: return
    if role=="organizer" and booking.get("organizer_id")==user_id: return
    raise AuthorizationError("You cannot manage this booking.")


def _money(value,label):
    try: result=Decimal(str(value))
    except (InvalidOperation,TypeError): raise ValidationError(f"{label} must be a valid amount.")
    if not result.is_finite() or result<0: raise ValidationError(f"{label} cannot be negative.")
    return result.quantize(Decimal("0.01"),rounding=ROUND_HALF_UP)


def _ensure_budget(cur,event_id):
    cur.execute("INSERT INTO budgets(event_id,total_amount) VALUES(%s,0) ON DUPLICATE KEY UPDATE event_id=VALUES(event_id)",(event_id,))
    cur.execute("SELECT * FROM budgets WHERE event_id=%s FOR UPDATE",(event_id,)); return cur.fetchone()


def _budget_totals(cur,event_id):
    cur.execute("SELECT COALESCE(SUM(allocated_amount),0) allocated,COALESCE(SUM(estimated_amount),0) item_estimate FROM budget_items WHERE budget_id=(SELECT id FROM budgets WHERE event_id=%s)",(event_id,)); items=cur.fetchone()
    cur.execute("SELECT total_amount FROM budgets WHERE event_id=%s",(event_id,)); budget=cur.fetchone(); budget_total=budget["total_amount"] if budget else 0
    cur.execute("SELECT COALESCE(SUM(amount),0) estimate FROM bookings WHERE event_id=%s AND status IN ('requested','confirmed')",(event_id,)); estimate_bookings=cur.fetchone()["estimate"]
    cur.execute("SELECT COALESCE(SUM(amount),0) spent FROM bookings WHERE event_id=%s AND status='confirmed'",(event_id,)); confirmed=cur.fetchone()["spent"]
    cur.execute("SELECT COALESCE(SUM(CASE WHEN record_type='charge' AND status IN ('success','refunded') THEN amount WHEN record_type='refund' AND status='success' THEN -amount ELSE 0 END),0) paid FROM payments p JOIN bookings b ON b.id=p.booking_id WHERE b.event_id=%s",(event_id,)); paid=cur.fetchone()["paid"]
    allocated=Decimal(str(items["allocated"])) or Decimal(str(budget_total)); estimated=Decimal(str(items["item_estimate"]))+Decimal(str(estimate_bookings)); spent=Decimal(str(confirmed))+Decimal(str(paid))
    return {"allocated":allocated,"estimated":estimated,"spent":spent,"remaining":allocated-spent,"variance":allocated-spent,"estimate_variance":allocated-estimated,"usage_percent":(spent/allocated*100 if allocated else Decimal(0))}


def _budget_alerts(cur,event_id,actor_id=None):
    cur.execute("SELECT b.id,b.total_amount,b.alert_80_sent,b.alert_exceeded_sent,e.owner_id,e.organizer_id FROM budgets b JOIN events e ON e.id=b.event_id WHERE b.event_id=%s FOR UPDATE",(event_id,)); budget=cur.fetchone()
    if not budget: return
    totals=_budget_totals(cur,event_id); allocated=totals["allocated"] or Decimal(str(budget["total_amount"]))
    spent=totals["spent"]; eighty=allocated>0 and spent>=allocated*Decimal("0.80"); over=allocated>0 and spent>allocated
    if eighty and not budget["alert_80_sent"]:
        for uid in {budget["owner_id"],budget["organizer_id"]}-{None}: _notify(cur,uid,f"Event budget has reached 80% usage ({spent} of {allocated}).")
        cur.execute("UPDATE budgets SET alert_80_sent=TRUE WHERE id=%s",(budget["id"],))
    elif not eighty and budget["alert_80_sent"]:
        cur.execute("UPDATE budgets SET alert_80_sent=FALSE WHERE id=%s",(budget["id"],))
    if over and not budget["alert_exceeded_sent"]:
        for uid in {budget["owner_id"],budget["organizer_id"]}-{None}: _notify(cur,uid,f"Event budget exceeded: spent {spent}, allocated {allocated}.")
        cur.execute("UPDATE budgets SET alert_exceeded_sent=TRUE WHERE id=%s",(budget["id"],))
    elif not over and budget["alert_exceeded_sent"]:
        cur.execute("UPDATE budgets SET alert_exceeded_sent=FALSE WHERE id=%s",(budget["id"],))


def refresh_budget_alerts(cur,event_id,actor_id=None):
    _budget_alerts(cur,event_id,actor_id)


def _generate_invoice(cur,booking_id):
    cur.execute("SELECT id FROM invoices WHERE booking_id=%s",(booking_id,))
    existing=cur.fetchone()
    cur.execute("""SELECT b.*,e.name event_name,e.owner_id client_id,v.name venue_name,vs.name service_name
      FROM bookings b JOIN events e ON e.id=b.event_id LEFT JOIN venues v ON v.id=b.venue_id
      LEFT JOIN vendor_services vs ON vs.id=b.service_id WHERE b.id=%s""",(booking_id,)); row=cur.fetchone()
    if not row: return
    amount=Decimal(str(row["amount"])); tax=(amount*Decimal(str(Config.INVOICE_TAX_PERCENT))/100).quantize(Decimal("0.01"),rounding=ROUND_HALF_UP)
    desc=row["service_name"] or row["venue_name"] or ("Vendor service" if row["vendor_id"] else "Venue booking")
    if existing:
        cur.execute("UPDATE invoices SET event_name=%s,client_id=%s,vendor_id=%s,description=%s,quantity=%s,amount=%s,tax=%s,total=%s WHERE id=%s",(row["event_name"],row["client_id"],row["vendor_id"],desc,row.get("quantity",1),amount,tax,amount+tax,existing["id"]))
        return
    cur.execute("""INSERT INTO invoices(booking_id,invoice_no,event_name,client_id,vendor_id,description,quantity,amount,tax,total,payment_status)
      VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'payment_pending')""",(booking_id,f"ERA-{booking_id:08d}",row["event_name"],row["client_id"],row["vendor_id"],desc,row.get("quantity",1),amount,tax,amount+tax))
    invoice_id=cur.lastrowid
    _notify(cur,row["client_id"],f"Invoice ERA-{booking_id:08d} is ready for event '{row['event_name']}'.")
    _audit(cur,row["client_id"],"INVOICE_GENERATED","invoices",invoice_id)


def ensure_invoice(cur,booking_id):
    _generate_invoice(cur,booking_id)


def confirmed_booking_changed(cur,booking_id,actor_id=None):
    _generate_invoice(cur,booking_id)
    cur.execute("SELECT event_id FROM bookings WHERE id=%s",(booking_id,)); row=cur.fetchone()
    if row: _budget_alerts(cur,row["event_id"],actor_id)


def budget_summary(user_id,role,event_id):
    with get_db_cursor() as (cur,_):
        event=_event(cur,event_id); _event_access(event,user_id,role)
        cur.execute("SELECT id FROM budgets WHERE event_id=%s",(event_id,)); budget=cur.fetchone()
        totals=_budget_totals(cur,event_id)
        cur.execute("SELECT * FROM budget_items WHERE budget_id=%s ORDER BY category",(budget["id"] if budget else None,)); items=cur.fetchall()
        for item in items:
            cur.execute("SELECT COALESCE(SUM(amount),0) amount FROM bookings WHERE event_id=%s AND budget_category=%s AND status='confirmed'",(event_id,item["category"])); item_spent=Decimal(str(cur.fetchone()["amount"]))
            cur.execute("SELECT COALESCE(SUM(CASE WHEN p.record_type='charge' AND p.status IN ('success','refunded') THEN p.amount WHEN p.record_type='refund' AND p.status='success' THEN -p.amount ELSE 0 END),0) amount FROM payments p JOIN bookings b ON b.id=p.booking_id WHERE b.event_id=%s AND b.budget_category=%s",(event_id,item["category"])); item_spent+=Decimal(str(cur.fetchone()["amount"]))
            item["spent_amount"]=item_spent
        return {"event_id":event_id,**totals,"items":items}


def set_budget(user_id,role,event_id,total_amount=None):
    with get_db_cursor() as (cur,_):
        event=_event(cur,event_id); _event_access(event,user_id,role); budget=_ensure_budget(cur,event_id)
        if total_amount is not None:
            total=_money(total_amount,"Budget total")
            cur.execute("UPDATE budgets SET total_amount=%s,alert_80_sent=FALSE,alert_exceeded_sent=FALSE WHERE id=%s",(total,budget["id"]))
        else:
            cur.execute("SELECT COALESCE(SUM(allocated_amount),0) total FROM budget_items WHERE budget_id=%s",(budget["id"],)); total=cur.fetchone()["total"]
            cur.execute("UPDATE budgets SET total_amount=%s WHERE id=%s",(total,budget["id"]))
        _audit(cur,user_id,"EVENT_BUDGET_UPDATED","budgets",budget["id"]); _notify(cur,event["owner_id"],f"Budget for '{event['name']}' was updated.")
        if event["organizer_id"] and event["organizer_id"]!=event["owner_id"]: _notify(cur,event["organizer_id"],f"Budget for '{event['name']}' was updated.")
        _budget_alerts(cur,event_id,user_id)


def budget_item_action(user_id,role,event_id,item_id,data,delete=False):
    data=data or {}
    category=str(data.get("category","")).strip()
    if not delete and not category: raise ValidationError("Budget category is required.")
    allocated=_money(data.get("allocated_amount",0),"Allocated amount") if not delete else None
    estimated=_money(data.get("estimated_amount",0),"Estimated amount") if not delete else None
    with get_db_cursor() as (cur,_):
        event=_event(cur,event_id); _event_access(event,user_id,role); budget=_ensure_budget(cur,event_id)
        if item_id:
            cur.execute("SELECT id FROM budget_items WHERE id=%s AND budget_id=%s FOR UPDATE",(item_id,budget["id"]))
            if not cur.fetchone(): raise NotFoundError("Budget item not found.")
        if delete: cur.execute("DELETE FROM budget_items WHERE id=%s",(item_id,)); action="BUDGET_ITEM_DELETED"; target=item_id
        elif item_id:
            cur.execute("UPDATE budget_items SET category=%s,allocated_amount=%s,estimated_amount=%s WHERE id=%s",(category,allocated,estimated,item_id)); action="BUDGET_ITEM_UPDATED"; target=item_id
        else:
            cur.execute("INSERT INTO budget_items(budget_id,category,allocated_amount,estimated_amount) VALUES(%s,%s,%s,%s)",(budget["id"],category,allocated,estimated)); target=cur.lastrowid; action="BUDGET_ITEM_CREATED"
        cur.execute("SELECT COALESCE(SUM(allocated_amount),0) total FROM budget_items WHERE budget_id=%s",(budget["id"],)); cur.execute("UPDATE budgets SET total_amount=%s WHERE id=%s",(cur.fetchone()["total"],budget["id"]))
        _audit(cur,user_id,action,"budget_items",target); _notify(cur,event["owner_id"],f"Budget category '{category or 'item'}' was changed.")
        if event["organizer_id"] and event["organizer_id"]!=event["owner_id"]: _notify(cur,event["organizer_id"],f"Budget category '{category or 'item'}' was changed.")
        _budget_alerts(cur,event_id,user_id)
        return target


def estimate_event(user_id,role,event_id):
    with get_db_cursor() as (cur,_):
        event=_event(cur,event_id); _event_access(event,user_id,role)
        cur.execute("""SELECT b.id,b.booking_type,b.amount,b.quantity,b.budget_category,COALESCE(v.name,vs.name) description
        FROM bookings b LEFT JOIN venues v ON v.id=b.venue_id LEFT JOIN vendor_services vs ON vs.id=b.service_id
        WHERE b.event_id=%s AND b.status IN ('requested','confirmed') ORDER BY b.id""",(event_id,)); items=cur.fetchall()
        return {"event_id":event_id,"estimated_total":sum((Decimal(str(item["amount"])) for item in items),Decimal("0.00")),"items":items}


def initiate_payment(user_id,role,booking_id,amount):
    amount=_money(amount,"Payment amount")
    if amount<=0: raise ValidationError("Payment amount must be greater than zero.")
    if role not in ("client","organizer"): raise AuthorizationError("Only the event client or assigned organizer can pay this booking.")
    with get_db_cursor() as (cur,_):
        cur.execute("SELECT b.*,e.owner_id,e.organizer_id,e.name event_name FROM bookings b JOIN events e ON e.id=b.event_id WHERE b.id=%s FOR UPDATE",(booking_id,)); booking=cur.fetchone()
        if not booking: raise NotFoundError("Booking not found.")
        _booking_access(booking,user_id,role)
        if booking["status"]!="confirmed": raise ConflictError("Payments are only accepted for confirmed bookings.")
        _generate_invoice(cur,booking_id)
        cur.execute("SELECT total FROM invoices WHERE booking_id=%s",(booking_id,)); invoice_total=Decimal(str(cur.fetchone()["total"]))
        cur.execute("SELECT COALESCE(SUM(CASE WHEN record_type='charge' AND status IN ('success','refunded') THEN amount WHEN record_type='refund' AND status='success' THEN -amount ELSE 0 END),0) paid,COALESCE(SUM(CASE WHEN record_type='charge' AND status='pending' AND (expires_at IS NULL OR expires_at>NOW()) THEN amount ELSE 0 END),0) reserved FROM payments WHERE booking_id=%s",(booking_id,)); payment_totals=cur.fetchone()
        paid=Decimal(str(payment_totals["paid"])); reserved=Decimal(str(payment_totals["reserved"]))
        outstanding=invoice_total-paid-reserved
        if amount>outstanding: raise ConflictError(f"Payment exceeds outstanding balance of {outstanding}.")
        gateway=get_gateway(); order=gateway.create_order(amount,Config.PAYMENT_CURRENCY,f"booking-{booking_id}-{secrets.token_hex(4)}")
        method="razorpay" if order["gateway"]=="razorpay" else "mock"
        placeholder=order["id"]
        cur.execute("INSERT INTO payments(booking_id,amount,method,status,transaction_id,gateway_order_id,record_type,initiated_by,expires_at) VALUES(%s,%s,%s,'pending',%s,%s,'charge',%s,DATE_ADD(NOW(),INTERVAL 30 MINUTE))",(booking_id,amount,method,placeholder,order["id"],user_id))
        payment_id=cur.lastrowid
        _audit(cur,user_id,"PAYMENT_INITIATED","payments",payment_id)
        _notify(cur,user_id,f"Payment for booking #{booking_id} was initiated. Complete it in the payment gateway.")
        return {"payment_record_id":payment_id,"order":order,"amount":str(amount),"currency":Config.PAYMENT_CURRENCY}


def _refresh_payment_status(cur,booking_id,actor_id):
    cur.execute("SELECT total FROM invoices WHERE booking_id=%s FOR UPDATE",(booking_id,)); invoice=cur.fetchone()
    cur.execute("SELECT COALESCE(SUM(CASE WHEN record_type='charge' AND status IN ('success','refunded') THEN amount WHEN record_type='refund' AND status='success' THEN -amount ELSE 0 END),0) paid,COALESCE(SUM(CASE WHEN record_type='refund' AND status='success' THEN amount ELSE 0 END),0) refunds FROM payments WHERE booking_id=%s",(booking_id,)); row=cur.fetchone()
    paid=Decimal(str(row["paid"])); refunded=Decimal(str(row["refunds"]))
    status="refunded" if refunded and paid<=0 else ("paid" if invoice and paid>=Decimal(str(invoice["total"])) else ("partially_paid" if paid>0 else "payment_pending"))
    cur.execute("UPDATE bookings SET payment_status=%s WHERE id=%s",(status,booking_id)); cur.execute("UPDATE invoices SET payment_status=%s WHERE booking_id=%s",(status,booking_id))
    cur.execute("SELECT event_id FROM bookings WHERE id=%s",(booking_id,)); event_id=cur.fetchone()["event_id"]
    _budget_alerts(cur,event_id,actor_id)


def verify_payment(user_id,role,payment_record_id,order_id,payment_id,signature):
    gateway=get_gateway()
    if not gateway.verify_payment(order_id,payment_id,signature):
        raise ValidationError("Payment signature verification failed.")
    with get_db_cursor() as (cur,_):
        if payment_record_id:
            cur.execute("SELECT p.*,b.event_id,b.status AS booking_status,e.owner_id,e.organizer_id FROM payments p JOIN bookings b ON b.id=p.booking_id JOIN events e ON e.id=b.event_id WHERE p.id=%s FOR UPDATE",(payment_record_id,))
        else:
            cur.execute("SELECT p.*,b.event_id,b.status AS booking_status,e.owner_id,e.organizer_id FROM payments p JOIN bookings b ON b.id=p.booking_id JOIN events e ON e.id=b.event_id WHERE p.gateway_order_id=%s FOR UPDATE",(order_id,))
        row=cur.fetchone()
        if not row: raise NotFoundError("Payment attempt not found.")
        _booking_access(row,user_id,role)
        if row["initiated_by"]!=user_id: raise AuthorizationError("Only the user who initiated this payment can verify it.")
        if row["gateway_order_id"]!=order_id: raise ValidationError("Payment order does not match this payment attempt.")
        if row["booking_status"]!="confirmed" and row["status"]=="pending":
            cur.execute("UPDATE payments SET status='failed' WHERE id=%s",(row["id"],)); _audit(cur,user_id,"PAYMENT_STATUS_FAILED","payments",row["id"])
            _notify(cur,user_id,f"Payment attempt for booking #{row['booking_id']} failed because the booking is no longer confirmed.")
            return {"payment_id":row["id"],"status":"failed"}
        if row["status"]=="success":
            if row["transaction_id"]==payment_id: return {"payment_id":row["id"],"status":"success","idempotent":True}
            raise ConflictError("This payment attempt was already completed.")
        if row["status"]!="pending": raise ConflictError("This payment attempt is no longer pending.")
        if row["expires_at"] and row["expires_at"]<=datetime.now(): raise ConflictError("This payment attempt has expired.")
        cur.execute("SELECT id FROM payments WHERE transaction_id=%s AND id<>%s",(payment_id,row["id"]))
        if cur.fetchone(): raise ConflictError("This gateway transaction was already recorded.")
        cur.execute("UPDATE payments SET status='success',transaction_id=%s,paid_at=NOW() WHERE id=%s",(payment_id,row["id"]))
        _refresh_payment_status(cur,row["booking_id"],user_id)
        for target in {row["owner_id"],row["organizer_id"]}-{None}: _notify(cur,target,f"A payment of {row['amount']} was recorded for booking #{row['booking_id']}.")
        _audit(cur,user_id,"PAYMENT_STATUS_SUCCESS","payments",row["id"])
        return {"payment_id":row["id"],"status":"success"}


def refund_booking_in_cursor(cur,booking_id,actor_id):
    cur.execute("SELECT id,initiated_by FROM payments WHERE booking_id=%s AND record_type='charge' AND status='pending' FOR UPDATE",(booking_id,)); pending=cur.fetchall()
    for payment in pending:
        cur.execute("UPDATE payments SET status='failed' WHERE id=%s",(payment["id"],))
        _audit(cur,actor_id,"PAYMENT_STATUS_FAILED","payments",payment["id"])
        _notify(cur,payment["initiated_by"],f"Payment attempt for cancelled booking #{booking_id} was closed.")
    cur.execute("SELECT * FROM payments WHERE booking_id=%s AND record_type='charge' AND status='success' FOR UPDATE",(booking_id,)); charges=cur.fetchall()
    if not charges:
        if pending:
            cur.execute("SELECT event_id FROM bookings WHERE id=%s",(booking_id,)); event=cur.fetchone()
            if event: _budget_alerts(cur,event["event_id"],actor_id)
        return
    for payment in charges:
        cur.execute("SELECT id FROM payments WHERE parent_payment_id=%s AND record_type='refund' AND status='success'",(payment["id"],))
        if cur.fetchone(): continue
        if payment["method"] not in ("mock","razorpay"):
            raise ConflictError("A refund for this legacy payment method must be processed manually.")
        gateway=get_gateway(payment["method"])
        result=gateway.refund(payment["transaction_id"],Decimal(str(payment["amount"])),f"booking-{booking_id}-refund-{payment['id']}")
        refund_id=result["id"]
        refund_status="success" if result.get("status") in ("processed","success") else "pending"
        if refund_status=="success": cur.execute("UPDATE payments SET status='refunded' WHERE id=%s",(payment["id"],))
        cur.execute("INSERT INTO payments(booking_id,amount,method,status,transaction_id,gateway_order_id,record_type,parent_payment_id,paid_at) VALUES(%s,%s,%s,%s,%s,%s,'refund',%s,NOW())",(booking_id,payment["amount"],payment["method"],refund_status,refund_id,payment.get("gateway_order_id"),payment["id"]))
        refund_record=cur.lastrowid
        _audit(cur,actor_id,"PAYMENT_REFUNDED" if refund_status=="success" else "PAYMENT_REFUND_PENDING","payments",refund_record)
    _refresh_payment_status(cur,booking_id,actor_id)
    cur.execute("SELECT event_id FROM bookings WHERE id=%s",(booking_id,)); event=cur.fetchone()
    if event: _notify(cur,actor_id,f"Payment refund for booking #{booking_id} was recorded.")


def list_invoices(user_id,role):
    sql="""SELECT i.*,b.event_id,b.booking_date,e.name AS event_title,v.business_name AS vendor_name
      FROM invoices i JOIN bookings b ON b.id=i.booking_id JOIN events e ON e.id=b.event_id LEFT JOIN vendors v ON v.user_id=i.vendor_id WHERE 1=1"""
    args=[]
    if role=="client": sql+=" AND i.client_id=%s"; args.append(user_id)
    elif role=="organizer": sql+=" AND e.organizer_id=%s"; args.append(user_id)
    elif role=="vendor": sql+=" AND i.vendor_id=%s"; args.append(user_id)
    elif role!="admin": return []
    sql+=" ORDER BY i.issued_at DESC"
    with get_db_cursor() as (cur,_): cur.execute(sql,tuple(args)); return cur.fetchall()


def invoice_details(user_id,role,invoice_id):
    with get_db_cursor() as (cur,_):
        cur.execute("""SELECT i.*,b.event_id,b.booking_date,b.start_time,b.end_time,e.name AS event_title,e.owner_id,e.organizer_id,
        e.event_date,v.business_name AS vendor_name,venue.name AS venue_name,client.name AS client_name
        FROM invoices i JOIN bookings b ON b.id=i.booking_id JOIN events e ON e.id=b.event_id
        LEFT JOIN vendors v ON v.user_id=i.vendor_id LEFT JOIN venues venue ON venue.id=b.venue_id JOIN users client ON client.id=i.client_id WHERE i.id=%s""",(invoice_id,)); invoice=cur.fetchone()
        if not invoice: raise NotFoundError("Invoice not found.")
        _booking_access(invoice,user_id,role)
        return invoice


def invoice_pdf(invoice):
    lines=[f"Invoice {invoice['invoice_no']}",f"Issued: {invoice['issued_at']}",f"Event: {invoice['event_title']}",f"Event date: {invoice['event_date']}",f"Client: {invoice['client_name']}",f"Vendor: {invoice.get('vendor_name') or 'Venue booking'}",f"Description: {invoice.get('description') or ''}",f"Quantity: {invoice['quantity']}",f"Amount: {invoice['amount']}",f"Tax: {invoice['tax']}",f"Total: {invoice['total']}",f"Payment status: {invoice['payment_status']}"]
    esc=lambda s:str(s).encode("ascii","replace").decode().replace("\\","\\\\").replace("(","\\(").replace(")","\\)")
    stream="BT /F1 11 Tf 50 790 Td 16 TL "+" ".join(f"({esc(line)}) Tj T*" for line in lines)+" ET"
    objects=["<< /Type /Catalog /Pages 2 0 R >>","<< /Type /Pages /Kids [3 0 R] /Count 1 >>","<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>","<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",f"<< /Length {len(stream.encode())} >>\nstream\n{stream}\nendstream"]
    pdf="%PDF-1.4\n"; offsets=[0]
    for index,obj in enumerate(objects,1): offsets.append(len(pdf.encode())); pdf+=f"{index} 0 obj\n{obj}\nendobj\n"
    xref=len(pdf.encode()); pdf+="xref\n0 6\n0000000000 65535 f \n"+"".join(f"{offset:010d} 00000 n \n" for offset in offsets[1:])+f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF"
    return pdf
