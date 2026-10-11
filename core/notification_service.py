"""Central notification entry point: in-app persistence plus async email/SMS adapters."""
import logging
import smtplib
from email.message import EmailMessage
from threading import Thread

from core.config import Config
from core.db import get_db_cursor

logger=logging.getLogger("era.notifications")


def _infer_event_type(message):
    text=str(message).lower()
    for needle,kind in (("verif","verification_result"),("invitation","invitation"),("rsvp","rsvp_confirmation"),("reminder","reminder"),("budget","budget_alert"),("payment","payment_confirmation"),("cancel","cancellation"),("schedule","schedule_change"),("venue","venue_change"),("booking","booking_update")):
        if needle in text: return kind
    return "general"


class SmsAdapter:
    """Replaceable SMS provider seam. This stub logs delivery intent without sending."""
    @staticmethod
    def send(phone,message):
        logger.info("SMS adapter stub received a delivery request.")


def _email(to_address,subject,message,link=None):
    if not to_address: return
    if not Config.SMTP_USER or not Config.SMTP_PASSWORD:
        logger.info("Email notification queued but SMTP credentials are not configured.")
        return
    try:
        email=EmailMessage(); email["Subject"]=subject; email["From"]=Config.SMTP_FROM; email["To"]=to_address
        email.set_content(message+(f"\n\nOpen: {link}" if link else ""))
        with smtplib.SMTP(Config.SMTP_HOST,Config.SMTP_PORT,timeout=15) as smtp:
            smtp.starttls(); smtp.login(Config.SMTP_USER,Config.SMTP_PASSWORD); smtp.send_message(email)
    except Exception as exc:
        logger.warning("Email notification delivery failed: %s",exc)


def _dispatch(channels,to_address,phone,subject,message,link):
    if "email" in channels and to_address:
        Thread(target=_email,args=(to_address,subject,message,link),daemon=True).start()
    if "sms" in channels and phone:
        Thread(target=SmsAdapter.send,args=(phone,message),daemon=True).start()


def notify_in_transaction(cursor,user_id,message,event_type="general",link=None,email_to=None,phone=None,subject=None,channels=("in_app","email","sms")):
    """Persist in-app notification using a caller's transaction; dispatch external channels asynchronously."""
    if not message: return None
    if event_type=="general": event_type=_infer_event_type(message)
    email=email_to; mobile=phone
    if user_id:
        cursor.execute("SELECT email,phone FROM users WHERE id=%s",(user_id,)); recipient=cursor.fetchone()
        if recipient:
            email=email or recipient["email"]; mobile=mobile or recipient["phone"]
            if "in_app" in channels:
                cursor.execute("INSERT INTO notifications(user_id,message,event_type,link,status) VALUES(%s,%s,%s,%s,'unread')",(user_id,str(message).strip(),event_type,link))
                notification_id=cursor.lastrowid
            else: notification_id=None
        else: notification_id=None
    else: notification_id=None
    _dispatch(channels,email,mobile,subject or f"ERA: {event_type.replace('_',' ').title()}",str(message).strip(),link)
    return notification_id


def notify(user_id,message,event_type="general",link=None,channels=("in_app","email","sms"),email_to=None,phone=None,subject=None):
    if not user_id and not email_to: return
    if event_type=="general": event_type=_infer_event_type(message)
    with get_db_cursor() as (cursor,_):
        return notify_in_transaction(cursor,user_id,message,event_type,link,email_to,phone,subject,channels)


def list_notifications(user_id,limit=50,unread_only=False):
    limit=max(1,min(int(limit),100))
    with get_db_cursor(commit_on_success=False) as (cursor,_):
        where="user_id=%s"+(" AND status='unread'" if unread_only else "")
        cursor.execute(f"SELECT id,message,event_type,link,status,created_at FROM notifications WHERE {where} ORDER BY created_at DESC,id DESC LIMIT %s",(user_id,limit))
        rows=cursor.fetchall()
        cursor.execute("SELECT COUNT(*) AS unread_count FROM notifications WHERE user_id=%s AND status='unread'",(user_id,))
        count=cursor.fetchone()["unread_count"]
        return rows,count


def mark_read(user_id,notification_id=None):
    with get_db_cursor() as (cursor,_):
        if notification_id:
            cursor.execute("UPDATE notifications SET status='read' WHERE id=%s AND user_id=%s",(notification_id,user_id))
            return cursor.rowcount>0
        cursor.execute("UPDATE notifications SET status='read' WHERE user_id=%s AND status='unread'",(user_id,))
        return cursor.rowcount
