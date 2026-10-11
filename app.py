"""
ERA: Event Resource & Administration System
Application Factory & Main Entry Point
"""

import os
from flask import Flask, jsonify, render_template, request, session
from core.config import Config
from core.errors import register_error_handlers
from core.security import get_csrf_token
from modules.auth import auth_bp
from modules.admin import admin_bp


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

    # Top-Level Root Routes
    @app.get("/")
    def index():
        return render_template("index.html", roles=Config.ROLES)

    @app.get("/dashboard")
    def dashboard():
        return render_template("index.html", roles=Config.ROLES)

    @app.get("/api/events")
    def get_events():
        return jsonify(
            success=True,
            events=[
                {
                    "id": 101,
                    "name": "Global Tech & AI Summit 2026",
                    "category": "Corporate",
                    "date": "2026-11-15",
                    "startTime": "09:00",
                    "endTime": "18:00",
                    "venue": "Grand Crystal Ballroom",
                    "budget": 25000,
                    "liveStatus": "Upcoming",
                    "progress": 75,
                    "description": "Annual Technology Innovation Conference",
                },
                {
                    "id": 102,
                    "name": "Royal Wedding Gala",
                    "category": "Wedding",
                    "date": "2026-12-05",
                    "startTime": "17:00",
                    "endTime": "23:30",
                    "venue": "Emerald Garden Pavilion",
                    "budget": 40000,
                    "liveStatus": "In-Progress",
                    "progress": 90,
                    "description": "Luxury Wedding & Reception",
                },
            ],
        )

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
