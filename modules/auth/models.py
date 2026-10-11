"""
ERA: Event Resource & Administration System
Auth Module Models
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from core.models import User, OrganizerProfile, ClientProfile, VendorProfile, VenueOwnerProfile, DeliveryPartnerProfile


@dataclass
class LoginAttempt:
    id: Optional[int]
    identifier: str
    failed_attempts: int
    locked_until: Optional[datetime]
    last_attempt_at: Optional[datetime]


@dataclass
class PasswordResetToken:
    id: Optional[int]
    user_id: int
    token: str
    expires_at: datetime
    used: bool
    created_at: Optional[datetime]
