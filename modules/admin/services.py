"""
ERA: Event Resource & Administration System
Admin Module Service Layer (Business Logic & Audit/Notification Hooks)
"""

import logging
from typing import Any, Dict, List, Optional

from core.config import Config
from core.errors import NotFoundError, ValidationError
from core.events import emit_event
from core.security import hash_password
from modules.admin.repositories import AdminRepository
from modules.bookings.lifecycle_service import admin_update_booking_status

logger = logging.getLogger("era.admin.service")


class AdminService:
    """Orchestrates administrative rules, verification processing, and oversight."""

    @staticmethod
    def get_dashboard_summary() -> Dict[str, Any]:
        """Fetches metric cards and recent timeline for admin dashboard."""
        return AdminRepository.get_dashboard_metrics()

    # ---------------- User Management ----------------

    @staticmethod
    def list_users(
        search: Optional[str] = None,
        role: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        return AdminRepository.get_users(search=search, role=role, status=status, limit=limit, offset=offset)

    @staticmethod
    def get_user_profile_detail(user_id: int) -> Dict[str, Any]:
        detail = AdminRepository.get_user_detail(user_id)
        if not detail:
            raise NotFoundError(f"User #{user_id} not found.")
        return detail

    @staticmethod
    def set_user_status(user_id: int, new_status: str, admin_id: int) -> Dict[str, Any]:
        """
        Activates, deactivates, or suspends a user.
        Writes audit log and notifies the affected user.
        """
        allowed = ("active", "inactive", "suspended", "pending")
        if new_status not in allowed:
            raise ValidationError(f"Invalid status. Choose from: {', '.join(allowed)}")

        if user_id == admin_id and new_status in ("inactive", "suspended"):
            raise ValidationError("You cannot deactivate or suspend your own administrator account.")

        user_data = AdminRepository.get_user_detail(user_id)
        if not user_data:
            raise NotFoundError("User not found.")

        AdminRepository.update_user_status(user_id, new_status)

        # Shared hook: Audit log + In-app notification
        emit_event(
            "user_status_changed",
            notify_user_id=user_id,
            notification_message=f"Your ERA account status has been changed to '{new_status}' by System Administration.",
            audit_action=f"USER_{new_status.upper()}",
            audit_entity="users",
            audit_entity_id=user_id,
            actor_id=admin_id,
            result="success",
        )

        return {"success": True, "message": f"User #{user_id} status updated to '{new_status}'."}

    @staticmethod
    def change_user_role(user_id: int, new_role: str, admin_id: int) -> Dict[str, Any]:
        """Changes user stakeholder role, writes audit log, notifies user."""
        if new_role not in Config.ROLES:
            raise ValidationError("Invalid role specified.")

        user_data = AdminRepository.get_user_detail(user_id)
        if not user_data:
            raise NotFoundError("User not found.")

        old_role = user_data["user"]["role"]
        AdminRepository.update_user_role(user_id, new_role)

        emit_event(
            "user_role_changed",
            notify_user_id=user_id,
            notification_message=f"Your ERA role was changed from {Config.ROLES.get(old_role, old_role)} to {Config.ROLES.get(new_role, new_role)}.",
            audit_action="CHANGE_USER_ROLE",
            audit_entity="users",
            audit_entity_id=user_id,
            actor_id=admin_id,
            result="success",
        )

        return {"success": True, "message": f"User #{user_id} role changed to '{new_role}'."}

    @staticmethod
    def reset_user_access(user_id: int, admin_id: int, temporary_password: Optional[str] = None) -> Dict[str, Any]:
        """Resets login lockouts and optionally sets a new temporary password."""
        user_data = AdminRepository.get_user_detail(user_id)
        if not user_data:
            raise NotFoundError("User not found.")

        pw_hash = hash_password(temporary_password) if temporary_password else None
        AdminRepository.reset_user_access(user_id, pw_hash)

        msg = "Your ERA account lockout has been cleared."
        if temporary_password:
            msg += f" A new temporary password was assigned by the system admin: {temporary_password}"

        emit_event(
            "user_access_reset",
            notify_user_id=user_id,
            notification_message=msg,
            audit_action="RESET_USER_ACCESS",
            audit_entity="users",
            audit_entity_id=user_id,
            actor_id=admin_id,
            result="success",
        )

        return {"success": True, "message": f"Access lockout for user #{user_id} was successfully cleared."}

    # ---------------- Verification Queue ----------------

    @staticmethod
    def get_verification_queue(status_filter: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        return AdminRepository.get_verification_queue(status_filter=status_filter, limit=limit, offset=offset)

    @staticmethod
    def process_verification_decision(
        doc_id: int,
        decision: str,
        admin_id: int,
        remarks: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Processes document and stakeholder verification:
        - decision in ('approve', 'reject', 'suspend')
        - updates document status & remarks
        - updates stakeholder 1:1 profile & users status
        - writes audit log
        - notifies user of outcome through shared event hook
        """
        valid_decisions = {
            "approve": ("approved", "verified"),
            "reject": ("rejected", "rejected"),
            "suspend": ("rejected", "suspended"),
        }
        if decision not in valid_decisions:
            raise ValidationError(f"Invalid verification decision '{decision}'. Use 'approve', 'reject', or 'suspend'.")

        doc_status, profile_status = valid_decisions[decision]
        remarks = (remarks or "").strip() or f"Decision {decision.upper()} issued by Administrator #{admin_id}"

        doc_row = AdminRepository.review_document(
            doc_id=doc_id,
            status=doc_status,
            reviewer_id=admin_id,
            remarks=remarks,
        )
        if not doc_row:
            raise NotFoundError("Verification document record not found.")

        target_user_id = doc_row["target_user_id"]
        role = doc_row["user_role"]

        # Update 1:1 stakeholder profile verification status and user status
        AdminRepository.update_stakeholder_verification(
            user_id=target_user_id,
            role=role,
            status=profile_status,
        )

        # Notify and Audit log via shared hook
        outcome_label = "Approved & Verified" if decision == "approve" else "Suspended" if decision == "suspend" else "Rejected"
        emit_event(
            "verification_outcome",
            notify_user_id=target_user_id,
            notification_message=f"Your ERA {Config.ROLES.get(role, role)} business verification has been {outcome_label}. Remarks: {remarks}",
            audit_action=f"VERIFY_{decision.upper()}",
            audit_entity="verification_documents",
            audit_entity_id=doc_id,
            actor_id=admin_id,
            result="success",
        )

        return {
            "success": True,
            "message": f"Verification for document #{doc_id} processed as '{decision.upper()}'. User status updated to '{profile_status}' and notified.",
        }

    # ---------------- Stakeholders, Venues, Bookings ----------------

    @staticmethod
    def list_stakeholders(role: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        return AdminRepository.get_stakeholders_by_role(role, limit, offset)

    @staticmethod
    def list_venues(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        return AdminRepository.get_all_venues(limit, offset)

    @staticmethod
    def set_venue_status(venue_id: int, status: str, admin_id: int) -> Dict[str, Any]:
        allowed = ("pending", "verified", "rejected", "suspended")
        if status not in allowed:
            raise ValidationError(f"Invalid venue status. Choose from: {', '.join(allowed)}")

        AdminRepository.update_venue_status(venue_id, status)

        emit_event(
            "venue_status_changed",
            audit_action=f"VENUE_{status.upper()}",
            audit_entity="venues",
            audit_entity_id=venue_id,
            actor_id=admin_id,
            result="success",
        )
        return {"success": True, "message": f"Venue #{venue_id} status updated to '{status}'."}

    @staticmethod
    def list_bookings(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        return AdminRepository.get_all_bookings(limit, offset)

    @staticmethod
    def set_booking_status(booking_id: int, status: str, admin_id: int, reason: Optional[str] = None) -> Dict[str, Any]:
        return admin_update_booking_status(booking_id, status, admin_id, "admin", reason)

    # ---------------- Payments & Audit Logs ----------------

    @staticmethod
    def list_all_payments(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        return AdminRepository.get_all_payments(limit, offset)

    @staticmethod
    def list_audit_logs(
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        date_query: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        return AdminRepository.get_audit_logs(user_id=user_id, action=action, date_query=date_query, limit=limit, offset=offset)
