from flask import jsonify, request, session
from core.decorators import login_required
from core.notification_service import list_notifications, mark_read
from modules.notifications import notifications_bp


@notifications_bp.get("/api/notifications")
@login_required
def notifications_list():
    try: rows,count=list_notifications(session["user_id"],request.args.get("limit",50),request.args.get("unread_only")=="true")
    except ValueError: return jsonify(success=False,message="limit must be an integer."),400
    return jsonify(success=True,notifications=rows,unread_count=count)


@notifications_bp.get("/api/notifications/count")
@login_required
def unread_count():
    _,count=list_notifications(session["user_id"],1,True)
    return jsonify(success=True,unread_count=count)


@notifications_bp.post("/api/notifications/<int:notification_id>/read")
@login_required
def notification_read(notification_id):
    if not mark_read(session["user_id"],notification_id): return jsonify(success=False,message="Notification not found."),404
    return jsonify(success=True)


@notifications_bp.post("/api/notifications/read-all")
@login_required
def notifications_read_all():
    return jsonify(success=True,updated=mark_read(session["user_id"]))
