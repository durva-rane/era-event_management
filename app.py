"""
ERA: Event Resource & Administration System
Application Factory & Main Entry Point
"""

import os
import logging
import time
from threading import Lock, Thread
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.exceptions import HTTPException
from core.config import Config
from core.errors import register_error_handlers
from core.security import get_csrf_token, validate_csrf_token
from modules.auth import auth_bp
from modules.admin import admin_bp
from modules.events import events_bp
from modules.vendors import vendors_bp
from modules.finance import finance_bp
from modules.attendees import attendees_bp
from modules.notifications import notifications_bp
from modules.delivery import delivery_bp
from modules.dashboard import dashboard_bp
from modules.reports import reports_bp

_reminder_lock = Lock()
_reminder_started = False


def _start_reminder_worker(app):
    global _reminder_started
    if not app.config.get("ENABLE_REMINDER_SCHEDULER", True):
        return
    with _reminder_lock:
        if _reminder_started:
            return
        _reminder_started = True

    def run():
        while True:
            time.sleep(60)
            try:
                from modules.attendees.services import send_due_reminders
                with app.app_context():
                    send_due_reminders()
            except Exception:
                app.logger.exception("Scheduled attendee reminders failed")
            time.sleep(900)

    Thread(target=run, name="era-event-reminders", daemon=True).start()


def create_app(config_class=Config):
    """
    Application Factory Pattern for ERA Platform.
    Configures database, security, blueprints, and error handlers.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)
    if app.config.get("TRUSTED_PROXY_HOPS", 0) > 0:
        hops = app.config["TRUSTED_PROXY_HOPS"]
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=hops, x_proto=hops, x_host=hops)

    # Ensure upload directories exist
    os.makedirs(Config.VERIFICATION_UPLOAD_FOLDER, exist_ok=True)

    # Global Context Processors (available in all Jinja templates)
    @app.context_processor
    def inject_global_template_vars():
        return {
            "csrf_token": get_csrf_token(),
            "roles": Config.ROLES,
            "current_user_id": session.get("user_id"),
            "current_user_name": session.get("user_name"),
            "current_user_role": session.get("user_role"),
            "current_user_status": session.get("user_status"),
        }

    # Register Global Error Handlers
    register_error_handlers(app)

    @app.before_request
    def security_request_checks():
        if app.config.get("FORCE_HTTPS") and not request.is_secure:
            return redirect(request.url.replace("http://", "https://", 1), code=308)
        if request.method not in ("GET", "HEAD", "OPTIONS") and not validate_csrf_token():
            return jsonify(success=False, message="CSRF validation failed. Refresh the page and try again."), 400

    @app.after_request
    def security_response_headers(response):
        token = get_csrf_token()
        response.set_cookie("era_csrf_token", token, secure=app.config["SESSION_COOKIE_SECURE"], httponly=False,
                            samesite="Lax", path="/")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault("Content-Security-Policy", "default-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'")
        if request.is_secure:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(vendors_bp)
    app.register_blueprint(finance_bp)
    app.register_blueprint(attendees_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(delivery_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(reports_bp)

    # Top-Level Root Routes
    @app.get("/")
    def index():
        return render_template("index.html", roles=Config.ROLES)

    @app.get("/dashboard")
    def dashboard():
        if session.get("user_id"):
            return redirect(url_for("dashboard.dashboard_page"))
        return render_template("index.html", roles=Config.ROLES)

    _start_reminder_worker(app)

    @app.errorhandler(Exception)
    def unexpected_error(error):
        if isinstance(error, HTTPException):
            return error
        app.logger.exception("Unhandled request exception")
        return jsonify(success=False, message="An internal server error occurred. Please try again later."), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=app.config.get("DEBUG", False), port=5000)
