"""
ERA: Event Resource & Administration System
Application Factory & Main Entry Point
"""

import os
import logging
import time
from threading import Lock, Thread
from flask import Flask, jsonify, render_template, request, session
from core.config import Config
from core.errors import register_error_handlers
from core.security import get_csrf_token
from modules.auth import auth_bp
from modules.admin import admin_bp
from modules.events import events_bp
from modules.vendors import vendors_bp
from modules.finance import finance_bp
from modules.attendees import attendees_bp
from modules.notifications import notifications_bp
from modules.delivery import delivery_bp

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

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(vendors_bp)
    app.register_blueprint(finance_bp)
    app.register_blueprint(attendees_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(delivery_bp)

    # Top-Level Root Routes
    @app.get("/")
    def index():
        return render_template("index.html", roles=Config.ROLES)

    @app.get("/dashboard")
    def dashboard():
        return render_template("index.html", roles=Config.ROLES)

    _start_reminder_worker(app)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
