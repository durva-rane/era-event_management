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
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-unsafe-change-this-secret")
    if FLASK_ENV == "production" and (SECRET_KEY.startswith("dev-only-") or len(SECRET_KEY) < 32):
        raise RuntimeError("Production requires a strong SECRET_KEY of at least 32 characters.")

    # Session settings
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=int(os.getenv("SESSION_TIMEOUT_MINUTES", "30")))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", str(FLASK_ENV == "production")).lower() == "true"
    SESSION_COOKIE_NAME = "era_session"
    SESSION_COOKIE_PATH = "/"
    PREFERRED_URL_SCHEME = "https" if FLASK_ENV == "production" else "http"
    FORCE_HTTPS = os.getenv("FORCE_HTTPS", str(FLASK_ENV == "production")).lower() == "true"
    TRUSTED_PROXY_HOPS = int(os.getenv("TRUSTED_PROXY_HOPS", "0"))

    # MySQL Database credentials
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "era_user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "era_db")
    ERA_COMMISSION_PERCENT = float(os.getenv("ERA_COMMISSION_PERCENT", "5"))
    PAYMENT_GATEWAY = os.getenv("PAYMENT_GATEWAY", "mock").lower()
    RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
    PAYMENT_CURRENCY = os.getenv("PAYMENT_CURRENCY", "INR")
    INVOICE_TAX_PERCENT = float(os.getenv("INVOICE_TAX_PERCENT", "0"))

    # SMTP Configuration
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM = os.getenv("SMTP_FROM", os.getenv("SMTP_USER", "noreply@era.com"))
    PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:5000")
    if FLASK_ENV == "production" and not PUBLIC_BASE_URL.startswith("https://"):
        raise RuntimeError("Production PUBLIC_BASE_URL must use HTTPS.")
    ENABLE_REMINDER_SCHEDULER = os.getenv("ENABLE_REMINDER_SCHEDULER", "true").lower() == "true"

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
