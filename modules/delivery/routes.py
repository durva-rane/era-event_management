from flask import jsonify, render_template, request, session

from core.decorators import role_required
from core.errors import AppError
from modules.delivery import delivery_bp
from modules.delivery import services


def _json_error(err):
    return jsonify(success=False, message=err.message), err.status_code


@delivery_bp.get("/delivery/tasks")
@role_required("delivery_partner")
def partner_dashboard():
    return render_template("delivery/partner.html", tasks=services.list_partner_tasks(session["user_id"]))


@delivery_bp.get("/deliveries")
@role_required("organizer")
def organizer_deliveries():
    return render_template("delivery/events.html", events=services.organizer_events(session["user_id"]))


@delivery_bp.get("/events/<int:event_id>/deliveries")
@role_required("organizer")
def organizer_tracking(event_id):
    try:
        tasks = services.list_event_tasks(event_id, session["user_id"], session["user_role"])
        return render_template("delivery/organizer.html", event_id=event_id, tasks=tasks)
    except AppError as err:
        return render_template("errors/error.html", code=err.status_code, message=err.message), err.status_code


@delivery_bp.get("/api/events/<int:event_id>/delivery-partners")
@role_required("organizer")
def partner_suggestions(event_id):
    try:
        return jsonify(success=True, partners=services.suggest_partners(event_id, session["user_id"], session["user_role"], request.args.get("scheduled_at", "")))
    except AppError as err:
        return _json_error(err)


@delivery_bp.post("/api/events/<int:event_id>/deliveries")
@role_required("organizer")
def create_delivery(event_id):
    try:
        task_id = services.create_task(event_id, session["user_id"], session["user_role"], request.get_json(silent=True) or request.form.to_dict())
        return jsonify(success=True, task_id=task_id), 201
    except AppError as err:
        return _json_error(err)


@delivery_bp.post("/api/deliveries/<int:task_id>/assign")
@role_required("organizer")
def assign_delivery(task_id):
    data = request.get_json(silent=True) or request.form.to_dict()
    try:
        services.assign_task(task_id, session["user_id"], session["user_role"], data.get("partner_id"))
        return jsonify(success=True, message="Delivery partner assigned.")
    except AppError as err:
        return _json_error(err)


@delivery_bp.get("/api/deliveries/<int:task_id>/tracking")
@role_required("organizer")
def delivery_tracking(task_id):
    try:
        task, timeline = services.tracking(task_id, session["user_id"], session["user_role"])
        return jsonify(success=True, task=task, timeline=timeline)
    except AppError as err:
        return _json_error(err)


@delivery_bp.post("/api/deliveries/<int:task_id>/status")
@role_required("delivery_partner", "organizer")
def update_delivery_status(task_id):
    data = request.get_json(silent=True) or request.form.to_dict()
    try:
        status = services.update_status(task_id, session["user_id"], session["user_role"], data.get("status"), data.get("note"))
        return jsonify(success=True, status=status)
    except AppError as err:
        return _json_error(err)


@delivery_bp.post("/api/deliveries/<int:task_id>/delay")
@role_required("delivery_partner")
def report_delivery_delay(task_id):
    data = request.get_json(silent=True) or request.form.to_dict()
    try:
        services.report_delay(task_id, session["user_id"], data.get("message"))
        return jsonify(success=True, message="Delay reported to the organizer.")
    except AppError as err:
        return _json_error(err)


@delivery_bp.post("/api/admin/delivery-partners/<int:partner_id>")
@role_required("admin")
def admin_manage_partner(partner_id):
    try:
        services.manage_partner(session["user_id"], partner_id, request.get_json(silent=True) or request.form.to_dict())
        return jsonify(success=True, message="Delivery partner profile updated.")
    except AppError as err:
        return _json_error(err)
