"""
ERA: Event Resource & Administration System
Admin Module Repository (Database Access Layer)
"""

from typing import Any, Dict, List, Optional
from core.db import get_db_cursor


class AdminRepository:
    """Encapsulates all database operations for administrative oversight."""

    # ---------------- Dashboard & Counts ----------------

    @staticmethod
    def get_dashboard_metrics() -> Dict[str, Any]:
        with get_db_cursor(commit_on_success=False) as (cursor, _):
            # Total users
            cursor.execute("SELECT COUNT(*) AS total, SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending FROM users")
            user_counts = cursor.fetchone() or {"total": 0, "pending": 0}

            # Pending verifications count (documents pending + users pending)
            cursor.execute("SELECT COUNT(*) AS cnt FROM verification_documents WHERE status = 'pending'")
            pending_docs = cursor.fetchone()["cnt"]

            # Events count
            cursor.execute("SELECT COUNT(*) AS cnt FROM events")
            total_events = cursor.fetchone()["cnt"]

            # Bookings count
            cursor.execute("SELECT COUNT(*) AS cnt FROM bookings")
            total_bookings = cursor.fetchone()["cnt"]

            # Payments total
            cursor.execute("SELECT COALESCE(SUM(amount), 0) AS total FROM payments WHERE status = 'success'")
            total_revenue = float(cursor.fetchone()["total"])

            # Recent audit logs
            cursor.execute(
                """
                SELECT a.*, u.name AS user_name, u.email AS user_email, u.role AS user_role
                FROM audit_logs a
                LEFT JOIN users u ON a.user_id = u.id
                ORDER BY a.created_at DESC
                LIMIT 8
                """
            )
            recent_logs = cursor.fetchall()

            return {
                "total_users": user_counts["total"],
                "pending_users": user_counts["pending"],
                "pending_verifications": pending_docs,
                "total_events": total_events,
                "total_bookings": total_bookings,
                "total_revenue": total_revenue,
                "recent_activity": recent_logs,
            }

    # ---------------- User Management ----------------

    @staticmethod
    def get_users(
        search: Optional[str] = None,
        role: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        query = ["SELECT id, name, email, phone, role, status, created_at, updated_at FROM users WHERE 1=1"]
        params = []

        if search:
            s = f"%{search.strip()}%"
            query.append("AND (name LIKE %s OR email LIKE %s OR phone LIKE %s)")
            params.extend([s, s, s])

        if role:
            query.append("AND role = %s")
            params.append(role)

        if status:
            query.append("AND status = %s")
            params.append(status)

        query.append("ORDER BY id DESC LIMIT %s OFFSET %s")
        params.extend([limit, offset])

        with get_db_cursor(commit_on_success=False) as (cursor, _):
            cursor.execute(" ".join(query), tuple(params))
            return cursor.fetchall()

    @staticmethod
    def get_user_detail(user_id: int) -> Optional[Dict[str, Any]]:
        with get_db_cursor(commit_on_success=False) as (cursor, _):
            cursor.execute("SELECT * FROM users WHERE id = %s LIMIT 1", (user_id,))
            user = cursor.fetchone()
            if not user:
                return None

            # Get 1:1 profile
            role = user["role"]
            table_map = {
                "organizer": "organizers",
                "client": "clients",
                "vendor": "vendors",
                "venue_owner": "venue_owners",
                "delivery_partner": "delivery_partners",
            }
            profile = None
            if role in table_map:
                cursor.execute(f"SELECT * FROM {table_map[role]} WHERE user_id = %s", (user_id,))
                profile = cursor.fetchone()

            # Get documents
            cursor.execute("SELECT * FROM verification_documents WHERE user_id = %s ORDER BY id DESC", (user_id,))
            docs = cursor.fetchall()

            return {"user": user, "profile": profile, "documents": docs}

    @staticmethod
    def update_user_status(user_id: int, status: str) -> bool:
        with get_db_cursor(commit_on_success=True) as (cursor, _):
            cursor.execute("UPDATE users SET status = %s WHERE id = %s", (status, user_id))
            return cursor.rowcount > 0

    @staticmethod
    def update_user_role(user_id: int, new_role: str) -> bool:
        with get_db_cursor(commit_on_success=True) as (cursor, _):
            cursor.execute("UPDATE users SET role = %s WHERE id = %s", (new_role, user_id))
            return cursor.rowcount > 0

    @staticmethod
    def reset_user_access(user_id: int, new_password_hash: Optional[str] = None) -> bool:
        with get_db_cursor(commit_on_success=True) as (cursor, _):
            # Clear lockout attempts
            cursor.execute(
                """
                DELETE FROM login_attempts
                WHERE identifier IN (SELECT email FROM users WHERE id = %s UNION SELECT phone FROM users WHERE id = %s)
                """,
                (user_id, user_id),
            )
            if new_password_hash:
                cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s", (new_password_hash, user_id))
            return True

    # ---------------- Verification Queue ----------------

    @staticmethod
    def get_verification_queue(status_filter: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        query = [
            """
            SELECT d.id AS doc_id, d.user_id, d.file_path, d.status AS doc_status, d.remarks, d.created_at,
                   u.name AS user_name, u.email AS user_email, u.phone AS user_phone, u.role, u.status AS user_status,
                   COALESCE(o.organization_name, v.business_name, vo.business_name, 'N/A') AS business_name,
                   COALESCE(o.verification_status, v.verification_status, vo.verification_status, 'pending') AS stakeholder_verification_status
            FROM verification_documents d
            JOIN users u ON d.user_id = u.id
            LEFT JOIN organizers o ON u.id = o.user_id
            LEFT JOIN vendors v ON u.id = v.user_id
            LEFT JOIN venue_owners vo ON u.id = vo.user_id
            WHERE 1=1
            """
        ]
        params = []
        if status_filter:
            query.append("AND d.status = %s")
            params.append(status_filter)

        query.append("ORDER BY d.id DESC LIMIT %s OFFSET %s")
        params.extend([limit, offset])

        with get_db_cursor(commit_on_success=False) as (cursor, _):
            cursor.execute(" ".join(query), tuple(params))
            return cursor.fetchall()

    @staticmethod
    def review_document(doc_id: int, status: str, reviewer_id: int, remarks: Optional[str]) -> Optional[Dict[str, Any]]:
        with get_db_cursor(commit_on_success=True) as (cursor, _):
            cursor.execute(
                """
                UPDATE verification_documents
                SET status = %s, reviewed_by = %s, remarks = %s
                WHERE id = %s
                """,
                (status, reviewer_id, remarks, doc_id),
            )
            cursor.execute(
                """
                SELECT d.*, u.id AS target_user_id, u.role AS user_role, u.email, u.name
                FROM verification_documents d
                JOIN users u ON d.user_id = u.id
                WHERE d.id = %s
                """,
                (doc_id,),
            )
            return cursor.fetchone()

    @staticmethod
    def update_stakeholder_verification(user_id: int, role: str, status: str) -> bool:
        """
        Updates the 1:1 profile verification_status and sets user.status = 'active' on approval,
        or 'suspended' / 'rejected' on rejection.
        """
        with get_db_cursor(commit_on_success=True) as (cursor, _):
            user_status = "active" if status == "verified" else "suspended" if status == "suspended" else "inactive" if status == "rejected" else "pending"
            cursor.execute("UPDATE users SET status = %s WHERE id = %s", (user_status, user_id))

            if role == "organizer":
                cursor.execute("UPDATE organizers SET verification_status = %s WHERE user_id = %s", (status, user_id))
            elif role == "vendor":
                cursor.execute("UPDATE vendors SET verification_status = %s WHERE user_id = %s", (status, user_id))
            elif role == "venue_owner":
                cursor.execute("UPDATE venue_owners SET verification_status = %s WHERE user_id = %s", (status, user_id))
            return True

    # ---------------- Stakeholder & Venue & Booking Entity Management ----------------

    @staticmethod
    def get_all_venues(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        with get_db_cursor(commit_on_success=False) as (cursor, _):
            cursor.execute(
                """
                SELECT v.*, u.name AS owner_name, u.email AS owner_email, u.phone AS owner_phone
                FROM venues v
                JOIN users u ON v.owner_id = u.id
                ORDER BY v.id DESC LIMIT %s OFFSET %s
                """, (limit, offset)
            )
            return cursor.fetchall()

    @staticmethod
    def update_venue_status(venue_id: int, status: str) -> bool:
        with get_db_cursor(commit_on_success=True) as (cursor, _):
            cursor.execute("UPDATE venues SET status = %s WHERE id = %s", (status, venue_id))
            return cursor.rowcount > 0

    @staticmethod
    def get_all_bookings(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        with get_db_cursor(commit_on_success=False) as (cursor, _):
            cursor.execute(
                """
                SELECT b.*, e.name AS event_name,
                       COALESCE(v.name, 'N/A') AS venue_name,
                       COALESCE(u.name, 'N/A') AS vendor_name
                FROM bookings b
                JOIN events e ON b.event_id = e.id
                LEFT JOIN venues v ON b.venue_id = v.id
                LEFT JOIN users u ON b.vendor_id = u.id
                ORDER BY b.id DESC LIMIT %s OFFSET %s
                """, (limit, offset)
            )
            return cursor.fetchall()

    @staticmethod
    def get_stakeholders_by_role(role: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        table_map = {
            "client": ("clients", "c.event_requirements, '' as details"),
            "organizer": ("organizers", "c.organization_name, c.specialization as details, c.verification_status"),
            "vendor": ("vendors", "c.business_name, c.service_type as details, c.pricing, c.location, c.verification_status"),
            "venue_owner": ("venue_owners", "c.business_name, c.license_number as details, c.ownership_type, c.verification_status"),
            "delivery_partner": ("delivery_partners", "c.availability as details, c.status as partner_status"),
        }
        if role not in table_map:
            return []
        table, extra_cols = table_map[role]

        with get_db_cursor(commit_on_success=False) as (cursor, _):
            cursor.execute(
                f"""
                SELECT u.id, u.name, u.email, u.phone, u.role, u.status, u.created_at,
                       {extra_cols}
                FROM users u
                JOIN {table} c ON u.id = c.user_id
                ORDER BY u.id DESC LIMIT %s OFFSET %s
                """, (limit, offset)
            )
            return cursor.fetchall()

    # ---------------- Payments ----------------

    @staticmethod
    def get_all_payments(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        with get_db_cursor(commit_on_success=False) as (cursor, _):
            cursor.execute(
                """
                SELECT p.*, b.booking_type, b.amount AS booking_amount, b.booking_date,
                       e.name AS event_name, u.name AS client_name, u.email AS client_email,
                       i.invoice_no, i.total AS invoice_total
                FROM payments p
                JOIN bookings b ON p.booking_id = b.id
                JOIN events e ON b.event_id = e.id
                JOIN users u ON e.owner_id = u.id
                LEFT JOIN invoices i ON b.id = i.booking_id
                ORDER BY p.id DESC LIMIT %s OFFSET %s
                """, (limit, offset)
            )
            return cursor.fetchall()

    # ---------------- Audit Logs Viewer ----------------

    @staticmethod
    def get_audit_logs(
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        date_query: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        query = [
            """
            SELECT a.*, u.name AS user_name, u.email AS user_email, u.role AS user_role
            FROM audit_logs a
            LEFT JOIN users u ON a.user_id = u.id
            WHERE 1=1
            """
        ]
        params = []

        if user_id:
            query.append("AND a.user_id = %s")
            params.append(user_id)

        if action:
            query.append("AND a.action = %s")
            params.append(action)

        if date_query:
            query.append("AND DATE(a.created_at) = %s")
            params.append(date_query)

        query.append("ORDER BY a.created_at DESC LIMIT %s OFFSET %s")
        params.extend([limit, offset])

        with get_db_cursor(commit_on_success=False) as (cursor, _):
            cursor.execute(" ".join(query), tuple(params))
            return cursor.fetchall()
