"""
ERA: Event Resource & Administration System
Auth Module Routes (HTTP Request/Response Layer Only)
"""

from datetime import datetime, timezone
from flask import flash, jsonify, redirect, render_template, request, session, url_for
from core.config import Config
from core.decorators import login_required
from core.errors import AppError, AuthenticationError, ConflictError, ValidationError
from modules.auth import auth_bp
from modules.auth.services import AuthService


def is_json_request() -> bool:
    return (
        request.path.startswith("/api/")
        or request.is_json
        or request.headers.get("Accept") == "application/json"
    )


# ==============================================================================
# REGISTRATION ROUTES
# ==============================================================================

@auth_bp.route("/register", methods=["GET"])
def register_page():
    """Renders stakeholder registration page."""
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return render_template("register.html", roles=Config.ROLES)


@auth_bp.route("/register", methods=["POST"])
@auth_bp.route("/api/register", methods=["POST"])
def register_action():
    """
    Handles user registration.
    Supports both JSON payloads and multipart/form-data for document uploads.
    """
    if request.is_json:
        data = request.get_json(silent=True) or {}
        files = {}
    else:
        data = request.form.to_dict()
        files = request.files

    try:
        result = AuthService.register_user(data, files)

        if is_json_request():
            return jsonify(
                success=True,
                message=result["message"],
                user_id=result["user_id"],
                requires_verification=result["requires_verification"],
                redirect_url=url_for("auth.login_page"),
            ), 201

        flash(result["message"], "success")
        return redirect(url_for("auth.login_page"))

    except AppError as err:
        if is_json_request():
            return jsonify(success=False, message=err.message), err.status_code
        flash(err.message, "danger")
        return redirect(url_for("auth.register_page"))
    except Exception as exc:
        auth_bp.logger.error(f"Unexpected registration error: {exc}")
        if is_json_request():
            return jsonify(success=False, message="Registration could not be completed. Please try again."), 500
        flash("An unexpected error occurred during registration.", "danger")
        return redirect(url_for("auth.register_page"))


# ==============================================================================
# LOGIN & LOGOUT ROUTES
# ==============================================================================

@auth_bp.route("/login", methods=["GET"])
def login_page():
    """Renders login page."""
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    next_url = request.args.get("next", "")
    return render_template("auth/login.html", roles=Config.ROLES, next=next_url)


@auth_bp.route("/login", methods=["POST"])
@auth_bp.route("/api/login", methods=["POST"])
def login_action():
    """
    Validates credentials, verifies status, enforces lockout, creates session.
    """
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.form.to_dict()

    identifier = data.get("identifier") or data.get("email") or data.get("loginIdentifier", "")
    password = data.get("password") or data.get("loginPassword", "")
    role = data.get("role") or data.get("loginRole")

    try:
        user = AuthService.authenticate_user(
            identifier=identifier,
            password=password,
            expected_role=role,
        )

        # Set session state
        session.clear()
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["user_email"] = user["email"]
        session["user_phone"] = user["phone"]
        session["user_role"] = user["role"]
        session["user_status"] = user["status"]
        session["last_active"] = datetime.now(timezone.utc).timestamp()
        session.permanent = True

        next_url = request.args.get("next") or data.get("next") or url_for("dashboard")

        if is_json_request():
            return jsonify(
                success=True,
                message=f"Welcome back, {user['name']}!",
                user=user,
                redirect_url=next_url,
            ), 200

        flash(f"Welcome back, {user['name']}!", "success")
        return redirect(next_url)

    except AppError as err:
        if is_json_request():
            return jsonify(success=False, message=err.message), err.status_code
        flash(err.message, "danger")
        return redirect(url_for("auth.login_page"))
    except Exception as exc:
        auth_bp.logger.error(f"Login error: {exc}")
        if is_json_request():
            return jsonify(success=False, message="Unable to process login at this time."), 500
        flash("An unexpected error occurred during login.", "danger")
        return redirect(url_for("auth.login_page"))


@auth_bp.route("/logout", methods=["GET", "POST"])
@auth_bp.route("/api/logout", methods=["POST"])
def logout_action():
    """Destroys current session and logs audit event."""
    user_id = session.get("user_id")
    AuthService.logout_user(user_id)
    session.clear()

    if is_json_request():
        return jsonify(success=True, message="Logged out successfully.", redirect_url=url_for("auth.login_page"))

    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login_page"))


# ==============================================================================
# FORGOT & RESET PASSWORD ROUTES
# ==============================================================================

@auth_bp.route("/forgot-password", methods=["GET"])
def forgot_password_page():
    return render_template("auth/forgot_password.html")


@auth_bp.route("/forgot-password", methods=["POST"])
@auth_bp.route("/api/forgot-password", methods=["POST"])
def forgot_password_action():
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.form.to_dict()

    email = data.get("email", "").strip()
    if not email:
        if is_json_request():
            return jsonify(success=False, message="Email address is required."), 400
        flash("Email address is required.", "danger")
        return redirect(url_for("auth.forgot_password_page"))

    result = AuthService.request_password_reset(email)

    if is_json_request():
        return jsonify(result), 200

    flash(result["message"], "info")
    return redirect(url_for("auth.login_page"))


@auth_bp.route("/reset-password/<token>", methods=["GET"])
def reset_password_page(token):
    return render_template("auth/reset_password.html", token=token)


@auth_bp.route("/reset-password/<token>", methods=["POST"])
@auth_bp.route("/api/reset-password/<token>", methods=["POST"])
def reset_password_action(token):
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.form.to_dict()

    new_password = data.get("password") or data.get("new_password", "")
    confirm_password = data.get("confirm_password", "")

    try:
        result = AuthService.reset_password(token, new_password, confirm_password)

        if is_json_request():
            return jsonify(result), 200

        flash(result["message"], "success")
        return redirect(url_for("auth.login_page"))

    except AppError as err:
        if is_json_request():
            return jsonify(success=False, message=err.message), err.status_code
        flash(err.message, "danger")
        return redirect(url_for("auth.reset_password_page", token=token))


# ==============================================================================
# USER PROFILE ROUTES
# ==============================================================================

@auth_bp.route("/profile", methods=["GET"])
@login_required
def profile_page():
    """Renders profile view/update page."""
    user_id = session["user_id"]
    profile_data = AuthService.get_user_profile(user_id)
    return render_template(
        "auth/profile.html",
        user=profile_data["user"],
        profile=profile_data["profile"],
        documents=profile_data["documents"],
        roles=Config.ROLES,
    )


@auth_bp.route("/profile", methods=["POST"])
@auth_bp.route("/api/profile", methods=["GET", "PUT", "POST"])
@login_required
def profile_api():
    user_id = session["user_id"]

    if request.method == "GET":
        profile_data = AuthService.get_user_profile(user_id)
        return jsonify(success=True, **profile_data)

    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.form.to_dict()

    try:
        result = AuthService.update_user_profile(user_id, data)
        # Update session name if changed
        if data.get("name"):
            session["user_name"] = data["name"].strip()

        if is_json_request():
            return jsonify(result), 200

        flash("Profile updated successfully.", "success")
        return redirect(url_for("auth.profile_page"))

    except AppError as err:
        if is_json_request():
            return jsonify(success=False, message=err.message), err.status_code
        flash(err.message, "danger")
        return redirect(url_for("auth.profile_page"))


@auth_bp.route("/pending-approval", methods=["GET"])
def pending_approval_page():
    """Informational page for accounts pending administrator review."""
    return render_template("auth/pending_approval.html")
