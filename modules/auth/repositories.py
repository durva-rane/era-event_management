"""
ERA: Event Resource & Administration System
Auth Module Database Repository (DB Access Layer Only)
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from core.db import get_db_cursor


class AuthRepository:
    """Encapsulates all SQL database access for authentication and profile management."""

    @staticmethod
    def find_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
        with get_db_cursor(commit_on_success=False) as (cursor, _):
            cursor.execute(
                "SELECT * FROM users WHERE id = %s LIMIT 1",
                (user_id,),
            )
            return cursor.fetchone()

    @staticmethod
    def find_user_by_email(email: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor(commit_on_success=False) as (cursor, _):
            cursor.execute(
                "SELECT * FROM users WHERE email = %s LIMIT 1",
                (email.strip().lower(),),
            )
            return cursor.fetchone()

    @staticmethod
    def find_user_by_phone(phone: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor(commit_on_success=False) as (cursor, _):
            cursor.execute(
                "SELECT * FROM users WHERE phone = %s LIMIT 1",
                (phone.strip(),),
            )
            return cursor.fetchone()

    @staticmethod
    def find_user_by_identifier(identifier: str) -> Optional[Dict[str, Any]]:
        """Finds user by email or phone or name."""
        clean = identifier.strip().lower()
        with get_db_cursor(commit_on_success=False) as (cursor, _):
            cursor.execute(
                """
                SELECT * FROM users
                WHERE email = %s OR phone = %s OR name = %s
                LIMIT 1
                """,
                (clean, identifier.strip(), identifier.strip()),
            )
            return cursor.fetchone()

    @staticmethod
    def create_user(
        name: str,
        email: str,
        phone: str,
        password_hash: str,
        role: str,
        status: str = "active"
    ) -> int:
        with get_db_cursor(commit_on_success=True) as (cursor, _):
            cursor.execute(
                """
                INSERT INTO users (name, email, phone, password_hash, role, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (name, email.strip().lower(), phone.strip(), password_hash, role, status),
            )
            return cursor.lastrowid

    @staticmethod
    def update_user_password(user_id: int, password_hash: str) -> bool:
        with get_db_cursor(commit_on_success=True) as (cursor, _):
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (password_hash, user_id),
            )
            return cursor.rowcount > 0

    @staticmethod
    def update_user_basic_info(user_id: int, name: str, phone: str) -> bool:
        with get_db_cursor(commit_on_success=True) as (cursor, _):
            cursor.execute(
                "UPDATE users SET name = %s, phone = %s WHERE id = %s",
                (name, phone, user_id),
            )
            return cursor.rowcount > 0

    # ---------------- Profile Repositories (1:1 with User) ----------------

    @staticmethod
    def create_organizer_profile(user_id: int, organization_name: str, specialization: str = None, verification_status: str = "pending") -> None:
        with get_db_cursor(commit_on_success=True) as (cursor, _):
            cursor.execute(
                """
                INSERT INTO organizers (user_id, organization_name, specialization, verification_status)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE organization_name=VALUES(organization_name), specialization=VALUES(specialization)
                """,
                (user_id, organization_name, specialization, verification_status),
            )

    @staticmethod
    def create_client_profile(user_id: int, event_requirements: str = None) -> None:
        with get_db_cursor(commit_on_success=True) as (cursor, _):
            cursor.execute(
                """
                INSERT INTO clients (user_id, event_requirements)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE event_requirements=VALUES(event_requirements)
                """,
                (user_id, event_requirements),
            )

    @staticmethod
    def create_vendor_profile(user_id: int, business_name: str, service_type: str, description: str = None, pricing: float = 0.0, location: str = None, verification_status: str = "pending") -> None:
        with get_db_cursor(commit_on_success=True) as (cursor, _):
            cursor.execute(
                """
                INSERT INTO vendors (user_id, business_name, service_type, description, pricing, location, verification_status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    business_name=VALUES(business_name),
                    service_type=VALUES(service_type),
                    description=VALUES(description),
                    pricing=VALUES(pricing),
                    location=VALUES(location)
                """,
                (user_id, business_name, service_type, description, pricing, location, verification_status),
            )

    @staticmethod
    def create_venue_owner_profile(user_id: int, business_name: str, ownership_type: str = "individual", license_number: str = None, verification_status: str = "pending") -> None:
        with get_db_cursor(commit_on_success=True) as (cursor, _):
            cursor.execute(
                """
                INSERT INTO venue_owners (user_id, ownership_type, business_name, license_number, verification_status)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    ownership_type=VALUES(ownership_type),
                    business_name=VALUES(business_name),
                    license_number=VALUES(license_number)
                """,
                (user_id, ownership_type, business_name, license_number, verification_status),
            )

    @staticmethod
    def create_delivery_partner_profile(user_id: int, availability: str = "available", status: str = "active") -> None:
        with get_db_cursor(commit_on_success=True) as (cursor, _):
            cursor.execute(
                """
                INSERT INTO delivery_partners (user_id, availability, status)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE availability=VALUES(availability), status=VALUES(status)
                """,
                (user_id, availability, status),
            )

    @staticmethod
    def get_role_profile(user_id: int, role: str) -> Optional[Dict[str, Any]]:
        table_map = {
            "organizer": "organizers",
            "client": "clients",
            "vendor": "vendors",
            "venue_owner": "venue_owners",
            "delivery_partner": "delivery_partners",
        }
        table = table_map.get(role)
        if not table:
            return None
        with get_db_cursor(commit_on_success=False) as (cursor, _):
            cursor.execute(f"SELECT * FROM {table} WHERE user_id = %s LIMIT 1", (user_id,))
            return cursor.fetchone()

    # ---------------- Verification Documents ----------------

    @staticmethod
    def add_verification_document(user_id: int, file_path: str, remarks: str = None) -> int:
        with get_db_cursor(commit_on_success=True) as (cursor, _):
            cursor.execute(
                """
                INSERT INTO verification_documents (user_id, file_path, status, remarks)
                VALUES (%s, %s, 'pending', %s)
                """,
                (user_id, file_path, remarks),
            )
            return cursor.lastrowid

    @staticmethod
    def get_user_documents(user_id: int) -> List[Dict[str, Any]]:
        with get_db_cursor(commit_on_success=False) as (cursor, _):
            cursor.execute(
                "SELECT * FROM verification_documents WHERE user_id = %s ORDER BY id DESC",
                (user_id,),
            )
            return cursor.fetchall()

    # ---------------- Account Lockout (5 attempts, 15 min) ----------------

    @staticmethod
    def get_login_attempt(identifier: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor(commit_on_success=False) as (cursor, _):
            cursor.execute(
                "SELECT * FROM login_attempts WHERE identifier = %s LIMIT 1",
                (identifier.strip().lower(),),
            )
            return cursor.fetchone()

    @staticmethod
    def record_failed_login(identifier: str, max_attempts: int = 5, lock_minutes: int = 15) -> Dict[str, Any]:
        """
        Increments failed attempt count.
        If failed attempts >= max_attempts, locks account until now + lock_minutes.
        """
        clean_ident = identifier.strip().lower()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        with get_db_cursor(commit_on_success=True) as (cursor, _):
            cursor.execute(
                "SELECT * FROM login_attempts WHERE identifier = %s LIMIT 1",
                (clean_ident,),
            )
            row = cursor.fetchone()

            if not row:
                failed = 1
                locked_until = None
                cursor.execute(
                    """
                    INSERT INTO login_attempts (identifier, failed_attempts, locked_until)
                    VALUES (%s, %s, %s)
                    """,
                    (clean_ident, failed, locked_until),
                )
            else:
                failed = row["failed_attempts"] + 1
                locked_until = row["locked_until"]

                if failed >= max_attempts:
                    locked_until = now + timedelta(minutes=lock_minutes)

                cursor.execute(
                    """
                    UPDATE login_attempts
                    SET failed_attempts = %s, locked_until = %s
                    WHERE identifier = %s
                    """,
                    (failed, locked_until, clean_ident),
                )

            return {"failed_attempts": failed, "locked_until": locked_until}

    @staticmethod
    def reset_login_attempts(identifier: str) -> None:
        clean_ident = identifier.strip().lower()
        with get_db_cursor(commit_on_success=True) as (cursor, _):
            cursor.execute(
                "DELETE FROM login_attempts WHERE identifier = %s",
                (clean_ident,),
            )

    # ---------------- Password Reset Tokens ----------------

    @staticmethod
    def create_password_reset_token(user_id: int, token: str, expires_at: datetime) -> int:
        with get_db_cursor(commit_on_success=True) as (cursor, _):
            # Invalidate older tokens for this user
            cursor.execute(
                "UPDATE password_reset_tokens SET used = 1 WHERE user_id = %s",
                (user_id,),
            )
            cursor.execute(
                """
                INSERT INTO password_reset_tokens (user_id, token, expires_at, used)
                VALUES (%s, %s, %s, 0)
                """,
                (user_id, token, expires_at),
            )
            return cursor.lastrowid

    @staticmethod
    def find_valid_reset_token(token: str) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        with get_db_cursor(commit_on_success=False) as (cursor, _):
            cursor.execute(
                """
                SELECT * FROM password_reset_tokens
                WHERE token = %s AND used = 0 AND expires_at > %s
                LIMIT 1
                """,
                (token, now),
            )
            return cursor.fetchone()

    @staticmethod
    def mark_reset_token_used(token_id: int) -> None:
        with get_db_cursor(commit_on_success=True) as (cursor, _):
            cursor.execute(
                "UPDATE password_reset_tokens SET used = 1 WHERE id = %s",
                (token_id,),
            )
