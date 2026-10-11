"""
ERA: Event Resource & Administration System
Core Configuration Module
"""

import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """Application configuration loaded from environment variables."""
    SECRET_KEY = os.getenv("SECRET_KEY", "era-secure-key-2026-production-session-token")

    # Session settings
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=int(os.getenv("SESSION_TIMEOUT_MINUTES", "30")))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("FLASK_ENV") == "production"

    # MySQL Database credentials
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "era_user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "SEPro@22")
    DB_NAME = os.getenv("DB_NAME", "era_db")

    # SMTP Configuration
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM = os.getenv("SMTP_FROM", os.getenv("SMTP_USER", "noreply@era.com"))

    # File Uploads
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    VERIFICATION_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, "verification_docs")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "doc", "docx"}

    # Roles Definition
    ROLES = {
        "client": "Client",
        "organizer": "Event Organizer",
        "venue_owner": "Venue Owner",
        "vendor": "Vendor / Supplier",
        "attendee": "Attendee",
        "delivery_partner": "Delivery Partner",
        "admin": "System Administrator",
    }
