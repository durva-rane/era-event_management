"""
ERA: Event Resource & Administration System
Auth Module Service Layer (Business Rules & Domain Logic)
"""

import logging
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Any, Dict, Optional, Tuple

from core.audit_logger import log_audit
from core.config import Config
from core.errors import AuthenticationError, ConflictError, NotFoundError, ValidationError
from core.security import generate_secure_token, hash_password, save_uploaded_file, verify_password
from core.validators import clean_phone, validate_email, validate_password, validate_phone
from modules.auth.repositories import AuthRepository

logger = logging.getLogger("era.auth.service")


class AuthService:
    """Implements all business workflows for Authentication and Profile Management."""

    @staticmethod
    def register_user(form_data: Dict[str, Any], files: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Registers a new stakeholder:
        - Validates input format and uniqueness
        - Determines initial status (active vs pending verification)
        - Hashes password
        - Creates 1:1 role profile
        - Saves verification documents if uploaded
        - Logs audit record
        """
        files = files or {}
        role = str(form_data.get("role", "")).strip().lower()
        name = str(form_data.get("name", "")).strip()
        email = str(form_data.get("email", "")).strip().lower()
        phone = clean_phone(str(form_data.get("phone", "")).strip())
        password = str(form_data.get("password", ""))
        confirm_password = str(form_data.get("confirm_password", ""))

        if role not in Config.ROLES:
            raise ValidationError("Invalid stakeholder role selected.")

        if not name or len(name) < 2:
            raise ValidationError("A valid full name or business representative name is required.")

        if not validate_email(email):
            raise ValidationError("Enter a valid email address.")

        if not validate_phone(phone):
            raise ValidationError("Enter a valid 10-digit Indian mobile number.")

        is_pw_valid, pw_err = validate_password(password)
        if not is_pw_valid:
            raise ValidationError(pw_err)

        if password != confirm_password:
            raise ValidationError("Passwords do not match.")

        # Check uniqueness
        if AuthRepository.find_user_by_email(email):
            raise ConflictError("An account with this email address already exists.")

        if AuthRepository.find_user_by_phone(phone):
            raise ConflictError("An account with this mobile phone number already exists.")

        # Role-based status determination
        # Vendors, venue owners, and organizers get status='pending' until verified
        # Clients and attendees become active immediately
        if role in ("vendor", "venue_owner", "organizer"):
            initial_status = "pending"
            verification_status = "pending"
        else:
            initial_status = "active"
            verification_status = "verified"

        # Hash password securely
        pw_hash = hash_password(password)

        # Create user
        user_id = AuthRepository.create_user(
            name=name,
            email=email,
            phone=phone,
            password_hash=pw_hash,
            role=role,
            status=initial_status,
        )

        # Create 1:1 Profile
        if role == "client":
            reqs = form_data.get("event_requirements", form_data.get("organization", ""))
            AuthRepository.create_client_profile(user_id=user_id, event_requirements=reqs)

        elif role == "organizer":
            org_name = form_data.get("organization") or form_data.get("organization_name") or name
            spec = form_data.get("specialization", "Corporate & Social Events")
            AuthRepository.create_organizer_profile(
                user_id=user_id,
                organization_name=org_name,
                specialization=spec,
                verification_status=verification_status,
            )

        elif role == "venue_owner":
            biz_name = form_data.get("organization") or form_data.get("business_name") or name
            ownership = form_data.get("ownership_type", "individual")
            license_no = form_data.get("license_number", "")
            AuthRepository.create_venue_owner_profile(
                user_id=user_id,
                business_name=biz_name,
                ownership_type=ownership,
                license_number=license_no,
                verification_status=verification_status,
            )

        elif role == "vendor":
            biz_name = form_data.get("organization") or form_data.get("business_name") or name
            service_type = form_data.get("service_type", "Catering & Event Services")
            desc = form_data.get("description", "")
            pricing = float(form_data.get("pricing") or 0.0)
            loc = form_data.get("city") or form_data.get("location") or "Mumbai"
            AuthRepository.create_vendor_profile(
                user_id=user_id,
                business_name=biz_name,
                service_type=service_type,
                description=desc,
                pricing=pricing,
                location=loc,
                verification_status=verification_status,
            )

        elif role == "delivery_partner":
            AuthRepository.create_delivery_partner_profile(
                user_id=user_id,
                availability="available",
                status="active",
            )

        # Handle document upload if provided
        doc_file = files.get("verification_doc") or files.get("document")
        if doc_file and doc_file.filename:
            try:
                doc_path = save_uploaded_file(doc_file, subfolder="verification_docs")
                AuthRepository.add_verification_document(
                    user_id=user_id,
                    file_path=doc_path,
                    remarks=f"Uploaded upon {role} registration",
                )
            except Exception as exc:
                logger.warning(f"Could not store uploaded document: {exc}")

        # Audit Log
        log_audit(
            action="REGISTER",
            entity="users",
            entity_id=user_id,
            user_id=user_id,
            result="success",
        )

        return {
            "user_id": user_id,
            "name": name,
            "email": email,
            "role": role,
            "status": initial_status,
            "requires_verification": (initial_status == "pending"),
            "message": (
                "Registration successful! Your business verification documents are under review by system administrators."
                if initial_status == "pending"
                else "Registration successful! You may now log in to your dashboard."
            ),
        }

    @staticmethod
    def authenticate_user(identifier: str, password: str, expected_role: Optional[str] = None) -> Dict[str, Any]:
        """
        Authenticates user with:
        - 5-attempt lockout per 15 minutes
        - Password verification
        - Inactive/suspended/pending status checks
        - Audit logging
        """
        ident = identifier.strip()
        if not ident:
            raise ValidationError("Please enter your email or mobile phone number.")

        if not password:
            raise ValidationError("Please enter your password.")

        # Check account lockout status
        attempt_record = AuthRepository.get_login_attempt(ident)
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        if attempt_record and attempt_record.get("locked_until"):
            locked_until = attempt_record["locked_until"]
            if now < locked_until:
                remaining_min = max(1, int((locked_until - now).total_seconds() / 60))
                log_audit(action="LOGIN", entity="users", result="denied")
                raise AuthenticationError(
                    f"Account is temporarily locked due to 5 consecutive failed login attempts. "
                    f"Please try again after {remaining_min} minute(s)."
                )

        # Lookup user
        user = AuthRepository.find_user_by_identifier(ident)
        if not user:
            # Increment failed attempt
            record = AuthRepository.record_failed_login(ident, max_attempts=5, lock_minutes=15)
            log_audit(action="LOGIN", entity="users", result="failure")
            failed = record["failed_attempts"]
            left = max(0, 5 - failed)
            if left == 0:
                raise AuthenticationError("Account locked. 5 failed login attempts exceeded. Try again after 15 minutes.")
            raise AuthenticationError(f"Invalid email/phone or password. ({left} attempt(s) remaining)")

        # Verify password
        if not verify_password(user["password_hash"], password):
            record = AuthRepository.record_failed_login(ident, max_attempts=5, lock_minutes=15)
            log_audit(action="LOGIN", entity="users", entity_id=user["id"], user_id=user["id"], result="failure")
            failed = record["failed_attempts"]
            left = max(0, 5 - failed)
            if left == 0:
                raise AuthenticationError("Account locked. 5 failed login attempts exceeded. Try again after 15 minutes.")
            raise AuthenticationError(f"Invalid credentials. ({left} attempt(s) remaining before lockout)")

        # Verify role match if specified
        if expected_role and user["role"] != expected_role and user["role"] != "admin":
            log_audit(action="LOGIN", entity="users", entity_id=user["id"], user_id=user["id"], result="denied")
            raise AuthenticationError(f"This account is registered as '{Config.ROLES.get(user['role'], user['role'])}', not '{Config.ROLES.get(expected_role, expected_role)}'.")

        # Check account status
        status = user["status"]
        if status == "pending":
            log_audit(action="LOGIN", entity="users", entity_id=user["id"], user_id=user["id"], result="denied")
            raise AuthenticationError(
                "Your account is pending verification by an administrator. "
                "Business documents are currently under review."
            )
        elif status == "suspended":
            log_audit(action="LOGIN", entity="users", entity_id=user["id"], user_id=user["id"], result="denied")
            raise AuthenticationError("Your account has been suspended. Please contact ERA system support.")
        elif status == "inactive":
            log_audit(action="LOGIN", entity="users", entity_id=user["id"], user_id=user["id"], result="denied")
            raise AuthenticationError("Your account is currently inactive. Please contact support.")

        # Successful login: Reset failed attempts
        AuthRepository.reset_login_attempts(ident)

        # Audit log success
        log_audit(action="LOGIN", entity="users", entity_id=user["id"], user_id=user["id"], result="success")

        return {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "phone": user["phone"],
            "role": user["role"],
            "status": user["status"],
        }

    @staticmethod
    def logout_user(user_id: Optional[int]) -> None:
        """Logs out user and writes audit entry."""
        if user_id:
            log_audit(action="LOGOUT", entity="users", entity_id=user_id, user_id=user_id, result="success")

    @staticmethod
    def request_password_reset(email: str) -> Dict[str, Any]:
        """
        Generates timed password reset token and sends email via SMTP.
        Always returns generic message to prevent email enumeration.
        """
        clean_email = email.strip().lower()
        user = AuthRepository.find_user_by_email(clean_email)

        token = generate_secure_token(32)
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).replace(tzinfo=None)

        if user:
            AuthRepository.create_password_reset_token(user_id=user["id"], token=token, expires_at=expires_at)
            log_audit(action="FORGOT_PASSWORD_REQUEST", entity="users", entity_id=user["id"], user_id=user["id"], result="success")

            # Send Email if configured
            try:
                AuthService._send_reset_email(user["email"], user["name"], token)
            except Exception as exc:
                logger.warning(f"Could not send password reset email via SMTP: {exc}")

        return {
            "success": True,
            "message": "If that email is registered in our system, you will receive password reset instructions.",
            "token": token if not Config.SMTP_USER else None,  # returned for dev/testing when SMTP is offline
        }

    @staticmethod
    def _send_reset_email(recipient: str, name: str, token: str) -> None:
        if not Config.SMTP_USER or not Config.SMTP_PASSWORD:
            logger.info(f"[DEV MODE] Password reset token for {recipient}: {token}")
            return

        msg = EmailMessage()
        msg["Subject"] = "ERA Platform - Password Reset Request"
        msg["From"] = Config.SMTP_FROM
        msg["To"] = recipient

        reset_url = f"http://127.0.0.1:5000/reset-password/{token}"
        msg.set_content(
            f"""Hello {name},

You requested to reset your password for the ERA Event Resource & Administration System.

Use the link below to set a new password (valid for 1 hour):
{reset_url}

If you did not make this request, please ignore this email.

Regards,
ERA Security Team
"""
        )

        with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
            server.send_message(msg)

    @staticmethod
    def reset_password(token: str, new_password: str, confirm_password: str) -> Dict[str, Any]:
        """Validates token and updates user password."""
        if not token:
            raise ValidationError("Password reset token is required.")

        is_valid, err_msg = validate_password(new_password)
        if not is_valid:
            raise ValidationError(err_msg)

        if new_password != confirm_password:
            raise ValidationError("Passwords do not match.")

        reset_record = AuthRepository.find_valid_reset_token(token)
        if not reset_record:
            raise ValidationError("This password reset link is invalid or has expired.")

        user_id = reset_record["user_id"]
        pw_hash = hash_password(new_password)

        AuthRepository.update_user_password(user_id, pw_hash)
        AuthRepository.mark_reset_token_used(reset_record["id"])

        log_audit(action="PASSWORD_RESET", entity="users", entity_id=user_id, user_id=user_id, result="success")

        return {"success": True, "message": "Your password has been reset successfully. You can now log in."}

    @staticmethod
    def get_user_profile(user_id: int) -> Dict[str, Any]:
        """Fetches base user + 1:1 Profile + documents."""
        user = AuthRepository.find_user_by_id(user_id)
        if not user:
            raise NotFoundError("User not found.")

        profile = AuthRepository.get_role_profile(user_id, user["role"]) or {}
        docs = AuthRepository.get_user_documents(user_id)

        return {
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "phone": user["phone"],
                "role": user["role"],
                "role_display": Config.ROLES.get(user["role"], user["role"]),
                "status": user["status"],
                "created_at": user["created_at"],
            },
            "profile": profile,
            "documents": docs,
        }

    @staticmethod
    def update_user_profile(user_id: int, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """Updates user basic details and 1:1 role profile details."""
        user = AuthRepository.find_user_by_id(user_id)
        if not user:
            raise NotFoundError("User not found.")

        name = form_data.get("name", user["name"]).strip()
        phone = clean_phone(form_data.get("phone", user["phone"]).strip())

        if name and len(name) >= 2:
            AuthRepository.update_user_basic_info(user_id, name, phone)

        role = user["role"]
        if role == "organizer":
            org = form_data.get("organization_name") or form_data.get("organization")
            spec = form_data.get("specialization")
            if org:
                AuthRepository.create_organizer_profile(user_id, org, spec)

        elif role == "client":
            reqs = form_data.get("event_requirements")
            if reqs:
                AuthRepository.create_client_profile(user_id, reqs)

        elif role == "venue_owner":
            biz = form_data.get("business_name") or form_data.get("organization")
            lic = form_data.get("license_number")
            ownership = form_data.get("ownership_type", "individual")
            if biz:
                AuthRepository.create_venue_owner_profile(user_id, biz, ownership, lic)

        elif role == "vendor":
            biz = form_data.get("business_name") or form_data.get("organization")
            stype = form_data.get("service_type")
            desc = form_data.get("description")
            pricing = float(form_data.get("pricing") or 0.0)
            loc = form_data.get("location") or form_data.get("city")
            if biz and stype:
                AuthRepository.create_vendor_profile(user_id, biz, stype, desc, pricing, loc)

        elif role == "delivery_partner":
            avail = form_data.get("availability", "available")
            stat = form_data.get("status", "active")
            AuthRepository.create_delivery_partner_profile(user_id, avail, stat)

        log_audit(action="UPDATE_PROFILE", entity="users", entity_id=user_id, user_id=user_id, result="success")

        return {"success": True, "message": "Profile updated successfully."}
