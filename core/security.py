"""
ERA: Event Resource & Administration System
Security & Cryptography Utilities
"""

import os
import secrets
from flask import session, request
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from core.config import Config


def hash_password(password: str) -> str:
    """Hashes password using secure scrypt/pbkdf2."""
    return generate_password_hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Verifies plain password against hash."""
    if not password_hash or not password:
        return False
    return check_password_hash(password_hash, password)


def generate_secure_token(nbytes: int = 32) -> str:
    """Generates cryptographically random URL-safe token."""
    return secrets.token_urlsafe(nbytes)


def get_csrf_token() -> str:
    """Retrieves or creates session CSRF token."""
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(32)
    return session["_csrf_token"]


def validate_csrf_token() -> bool:
    """Validates submitted CSRF token from header or form body."""
    # Exclude GET, HEAD, OPTIONS
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return True
    expected = session.get("_csrf_token")
    if not expected:
        return False
    # Check header or json or form
    token = (
        request.headers.get("X-CSRF-Token")
        or (request.get_json(silent=True) or {}).get("csrf_token")
        or request.form.get("csrf_token")
    )
    return bool(token and secrets.compare_digest(token, expected))


def allowed_file(filename: str) -> bool:
    """Checks if uploaded file extension is allowed."""
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in Config.ALLOWED_EXTENSIONS


def save_uploaded_file(file_storage, subfolder: str = "verification_docs") -> str:
    """
    Saves an uploaded file with randomized secure filename.
    Returns the relative path from static or uploads.
    """
    if not file_storage or not file_storage.filename:
        return ""
    if not allowed_file(file_storage.filename):
        raise ValueError("File type not permitted.")

    ext = file_storage.filename.rsplit(".", 1)[1].lower()
    safe_name = f"{secrets.token_hex(16)}.{ext}"

    target_dir = os.path.join(Config.UPLOAD_FOLDER, subfolder)
    os.makedirs(target_dir, exist_ok=True)

    dest_path = os.path.join(target_dir, safe_name)
    file_storage.save(dest_path)

    # Return web/database relative path
    return f"/uploads/{subfolder}/{safe_name}"
