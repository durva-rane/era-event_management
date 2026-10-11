"""
ERA: Event Resource & Administration System
Admin Module Models & DTOs
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class AdminDashboardMetrics:
    total_users: int
    pending_verifications: int
    total_events: int
    total_bookings: int
    total_revenue_inr: float
    recent_activity: List[Dict[str, Any]]


@dataclass
class VerificationQueueItem:
    doc_id: int
    user_id: int
    user_name: str
    user_email: str
    user_role: str
    business_name: Optional[str]
    doc_file_path: str
    doc_status: str
    verification_status: str
    created_at: datetime
    remarks: Optional[str] = None
