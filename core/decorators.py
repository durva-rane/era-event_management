"""
ERA: Event Resource & Administration System
Authentication & Role-Based Access Control (RBAC) Decorators
"""

from datetime import datetime, timezone
from functools import wraps
from flask import jsonify, redirect, request, session, url_for, flash
from core.config import Config


def _is_api_request() -> bool:
    """Detects whether request expects JSON response."""
    return (
        request.path.startswith("/api/")
        or request.headers.get("Accept") == "application/json"
        or request.is_json
    )


def login_required(f):
    """
    Enforces authentication and session inactivity timeout.
    Updates last_active on every valid request.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            if _is_api_request():
                return jsonify(success=False, message="Authentication required. Please log in."), 401
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login_page", next=request.url))

        # Check session inactivity timeout
        last_active = session.get("last_active")
        now = datetime.now(timezone.utc).timestamp()
        timeout_seconds = Config.PERMANENT_SESSION_LIFETIME.total_seconds()

        if last_active and (now - last_active > timeout_seconds):
            session.clear()
            if _is_api_request():
                return jsonify(success=False, message="Session timed out due to inactivity. Please log in again."), 401
            flash("Your session timed out due to inactivity. Please log in again.", "warning")
            return redirect(url_for("auth.login_page", next=request.url))

        session["last_active"] = now
        return f(*args, **kwargs)

    return decorated_function


def role_required(*roles):
    """
    Enforces role-based authorization (RBAC).
    User must have at least one of the listed roles.
    """
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            user_role = session.get("user_role")
            if user_role not in roles and user_role != "admin":
                if _is_api_request():
                    return jsonify(
                        success=False,
                        message=f"Access denied. Requires one of roles: {', '.join(roles)}"
                    ), 403
                flash("You do not have permission to access that section.", "danger")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)


        return decorated_function

    return decorator


def verified_required(f):
    """
    Blocks users whose status is pending, inactive, or suspended
    from accessing protected features.
    """
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        status = session.get("user_status", "pending")
        if status == "pending":
            msg = "Your account is currently pending administrator verification of your business documents."
            if _is_api_request():
                return jsonify(success=False, message=msg, status="pending"), 403
            flash(msg, "warning")
            return redirect(url_for("auth.profile_page"))
        elif status in ("inactive", "suspended"):
            msg = f"Your account is currently {status}. Please contact administrator support."
            if _is_api_request():
                return jsonify(success=False, message=msg, status=status), 403
            flash(msg, "danger")
            session.clear()
            return redirect(url_for("auth.login_page"))
        return f(*args, **kwargs)

    return decorated_function
