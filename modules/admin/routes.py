"""
ERA: Event Resource & Administration System
Admin Module Routes (HTTP Layer Only, Admin-Only RBAC)
"""

from flask import flash, jsonify, redirect, render_template, request, session, url_for
from core.config import Config
from core.decorators import role_required
from core.errors import AppError
from core.pagination import page_args
from modules.admin import admin_bp
from modules.admin.services import AdminService


def is_json_request() -> bool:
    return (
        request.path.startswith("/api/")
        or request.is_json
        or request.headers.get("Accept") == "application/json"
    )


def _page():
    _, size, offset = page_args(request.args)
    return size, offset


# ==============================================================================
# 1. ADMIN DASHBOARD
# ==============================================================================

@admin_bp.route("/admin", methods=["GET"])
@admin_bp.route("/admin/dashboard", methods=["GET"])
@role_required("admin")
def dashboard_view():
    metrics = AdminService.get_dashboard_summary()
    return render_template("admin/dashboard.html", metrics=metrics, roles=Config.ROLES)


@admin_bp.route("/api/admin/metrics", methods=["GET"])
@role_required("admin")
def api_metrics():
    metrics = AdminService.get_dashboard_summary()
    return jsonify(success=True, metrics=metrics)


# ==============================================================================
# 2. USER MANAGEMENT
# ==============================================================================

@admin_bp.route("/admin/users", methods=["GET"])
@role_required("admin")
def users_view():
    search = request.args.get("search", "").strip()
    role = request.args.get("role", "").strip()
    status = request.args.get("status", "").strip()

    size, offset = _page()
    users_list = AdminService.list_users(search=search or None, role=role or None, status=status or None, limit=size, offset=offset)
    return render_template(
        "admin/users.html",
        users=users_list,
        roles=Config.ROLES,
        current_search=search,
        current_role=role,
        current_status=status,
    )


@admin_bp.route("/api/admin/users", methods=["GET"])
@role_required("admin")
def api_users():
    search = request.args.get("search", "").strip()
    role = request.args.get("role", "").strip()
    status = request.args.get("status", "").strip()
    size, offset = _page()
    users_list = AdminService.list_users(search=search or None, role=role or None, status=status or None, limit=size, offset=offset)
    return jsonify(success=True, users=users_list)


@admin_bp.route("/api/admin/users/<int:user_id>/status", methods=["POST"])
@role_required("admin")
def api_update_user_status(user_id):
    data = request.get_json(silent=True) or request.form.to_dict()
    new_status = data.get("status")
    admin_id = session["user_id"]

    try:
        res = AdminService.set_user_status(user_id, new_status, admin_id)
        if is_json_request():
            return jsonify(res), 200
        flash(res["message"], "success")
        return redirect(url_for("admin.users_view"))
    except AppError as err:
        if is_json_request():
            return jsonify(success=False, message=err.message), err.status_code
        flash(err.message, "danger")
        return redirect(url_for("admin.users_view"))


@admin_bp.route("/api/admin/users/<int:user_id>/role", methods=["POST"])
@role_required("admin")
def api_update_user_role(user_id):
    data = request.get_json(silent=True) or request.form.to_dict()
    new_role = data.get("role")
    admin_id = session["user_id"]

    try:
        res = AdminService.change_user_role(user_id, new_role, admin_id)
        if is_json_request():
            return jsonify(res), 200
        flash(res["message"], "success")
        return redirect(url_for("admin.users_view"))
    except AppError as err:
        if is_json_request():
            return jsonify(success=False, message=err.message), err.status_code
        flash(err.message, "danger")
        return redirect(url_for("admin.users_view"))


@admin_bp.route("/api/admin/users/<int:user_id>/reset-access", methods=["POST"])
@role_required("admin")
def api_reset_user_access(user_id):
    data = request.get_json(silent=True) or request.form.to_dict()
    temp_pw = data.get("temporary_password")
    admin_id = session["user_id"]

    try:
        res = AdminService.reset_user_access(user_id, admin_id, temp_pw)
        if is_json_request():
            return jsonify(res), 200
        flash(res["message"], "success")
        return redirect(url_for("admin.users_view"))
    except AppError as err:
        if is_json_request():
            return jsonify(success=False, message=err.message), err.status_code
        flash(err.message, "danger")
        return redirect(url_for("admin.users_view"))


# ==============================================================================
# 3. VERIFICATION QUEUE
# ==============================================================================

@admin_bp.route("/admin/verifications", methods=["GET"])
@role_required("admin")
def verifications_view():
    status = request.args.get("status", "").strip()
    size, offset = _page()
    queue = AdminService.get_verification_queue(status_filter=status or None, limit=size, offset=offset)
    return render_template("admin/verifications.html", queue=queue, current_status=status, roles=Config.ROLES)


@admin_bp.route("/api/admin/verifications", methods=["GET"])
@role_required("admin")
def api_verifications():
    status = request.args.get("status", "").strip()
    size, offset = _page()
    queue = AdminService.get_verification_queue(status_filter=status or None, limit=size, offset=offset)
    return jsonify(success=True, queue=queue)


@admin_bp.route("/api/admin/verifications/<int:doc_id>/decision", methods=["POST"])
@role_required("admin")
def api_process_verification(doc_id):
    data = request.get_json(silent=True) or request.form.to_dict()
    decision = data.get("decision")  # 'approve', 'reject', 'suspend'
    remarks = data.get("remarks")
    admin_id = session["user_id"]

    try:
        res = AdminService.process_verification_decision(
            doc_id=doc_id,
            decision=decision,
            admin_id=admin_id,
            remarks=remarks,
        )
        if is_json_request():
            return jsonify(res), 200
        flash(res["message"], "success")
        return redirect(url_for("admin.verifications_view"))
    except AppError as err:
        if is_json_request():
            return jsonify(success=False, message=err.message), err.status_code
        flash(err.message, "danger")
        return redirect(url_for("admin.verifications_view"))


# ==============================================================================
# 4. MANAGE STAKEHOLDERS, VENUES & BOOKINGS
# ==============================================================================

@admin_bp.route("/admin/stakeholders/<role>", methods=["GET"])
@role_required("admin")
def stakeholders_view(role):
    size, offset = _page()
    items = AdminService.list_stakeholders(role, size, offset)
    role_name = Config.ROLES.get(role, role.title())
    return render_template("admin/stakeholders.html", items=items, role=role, role_name=role_name)


@admin_bp.route("/admin/venues", methods=["GET"])
@role_required("admin")
def venues_view():
    size, offset = _page()
    venues = AdminService.list_venues(size, offset)
    return render_template("admin/venues.html", venues=venues)


@admin_bp.route("/api/admin/venues/<int:venue_id>/status", methods=["POST"])
@role_required("admin")
def api_update_venue_status(venue_id):
    data = request.get_json(silent=True) or request.form.to_dict()
    status = data.get("status")
    admin_id = session["user_id"]

    try:
        res = AdminService.set_venue_status(venue_id, status, admin_id)
        if is_json_request():
            return jsonify(res), 200
        flash(res["message"], "success")
        return redirect(url_for("admin.venues_view"))
    except AppError as err:
        if is_json_request():
            return jsonify(success=False, message=err.message), err.status_code
        flash(err.message, "danger")
        return redirect(url_for("admin.venues_view"))


@admin_bp.route("/admin/bookings", methods=["GET"])
@role_required("admin")
def bookings_view():
    size, offset = _page()
    bookings = AdminService.list_bookings(size, offset)
    return render_template("admin/bookings.html", bookings=bookings)


@admin_bp.route("/api/admin/bookings/<int:booking_id>/status", methods=["POST"])
@role_required("admin")
def api_update_booking_status(booking_id):
    data = request.get_json(silent=True) or request.form.to_dict()
    status = data.get("status")
    admin_id = session["user_id"]

    try:
        res = AdminService.set_booking_status(booking_id, status, admin_id, data.get("reason"))
        if is_json_request():
            return jsonify(res), 200
        flash(res["message"], "success")
        return redirect(url_for("admin.bookings_view"))
    except AppError as err:
        if is_json_request():
            return jsonify(success=False, message=err.message), err.status_code
        flash(err.message, "danger")
        return redirect(url_for("admin.bookings_view"))


# ==============================================================================
# 5. PAYMENTS OVERVIEW
# ==============================================================================

@admin_bp.route("/admin/payments", methods=["GET"])
@role_required("admin")
def payments_view():
    size, offset = _page()
    payments = AdminService.list_all_payments(size, offset)
    return render_template("admin/payments.html", payments=payments)


@admin_bp.route("/api/admin/payments", methods=["GET"])
@role_required("admin")
def api_payments():
    size, offset = _page()
    payments = AdminService.list_all_payments(size, offset)
    return jsonify(success=True, payments=payments)


# ==============================================================================
# 6. AUDIT LOG VIEWER WITH FILTERS
# ==============================================================================

@admin_bp.route("/admin/audit-logs", methods=["GET"])
@role_required("admin")
def audit_logs_view():
    user_id = request.args.get("user_id", type=int)
    action = request.args.get("action", "").strip() or None
    date_query = request.args.get("date", "").strip() or None

    size, offset = _page()
    logs = AdminService.list_audit_logs(user_id=user_id, action=action, date_query=date_query, limit=size, offset=offset)
    return render_template(
        "admin/audit_logs.html",
        logs=logs,
        current_user_id=user_id or "",
        current_action=action or "",
        current_date=date_query or "",
    )


@admin_bp.route("/api/admin/audit-logs", methods=["GET"])
@role_required("admin")
def api_audit_logs():
    user_id = request.args.get("user_id", type=int)
    action = request.args.get("action", "").strip() or None
    date_query = request.args.get("date", "").strip() or None
    size, offset = _page()
    logs = AdminService.list_audit_logs(user_id=user_id, action=action, date_query=date_query, limit=size, offset=offset)
    return jsonify(success=True, logs=logs)
