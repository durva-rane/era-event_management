"""
ERA: Event Resource & Administration System
Core Domain Models (Entities, DTOs, and Computed Attributes)
"""

from dataclasses import dataclass, field
from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional, List


# ==============================================================================
# 1. USER & ROLE PROFILES
# ==============================================================================

@dataclass
class User:
    id: Optional[int]
    name: str
    email: str
    phone: str
    password_hash: str
    role: str  # 'client', 'organizer', 'vendor', 'venue_owner', 'attendee', 'delivery_partner', 'admin'
    status: str = "active"  # 'active', 'inactive', 'suspended', 'pending'
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class OrganizerProfile:
    user_id: int
    organization_name: str
    specialization: Optional[str] = None
    verification_status: str = "pending"  # 'pending', 'verified', 'rejected'
    created_at: Optional[datetime] = None


@dataclass
class ClientProfile:
    user_id: int
    event_requirements: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class VendorProfile:
    user_id: int
    business_name: str
    service_type: str
    description: Optional[str] = None
    pricing: Decimal = Decimal("0.00")
    location: Optional[str] = None
    verification_status: str = "pending"
    created_at: Optional[datetime] = None


@dataclass
class VenueOwnerProfile:
    user_id: int
    ownership_type: str = "individual"  # 'individual', 'corporate', 'partnership', 'lease'
    business_name: str = ""
    license_number: Optional[str] = None
    verification_status: str = "pending"
    created_at: Optional[datetime] = None


@dataclass
class DeliveryPartnerProfile:
    user_id: int
    availability: str = "available"  # 'available', 'busy', 'offline'
    status: str = "active"  # 'active', 'inactive', 'on_delivery'
    created_at: Optional[datetime] = None


@dataclass
class VerificationDocument:
    id: Optional[int]
    user_id: int
    file_path: str
    status: str = "pending"  # 'pending', 'approved', 'rejected'
    reviewed_by: Optional[int] = None
    remarks: Optional[str] = None
    created_at: Optional[datetime] = None


# ==============================================================================
# 2. VENUES & EVENTS
# ==============================================================================

@dataclass
class Venue:
    id: Optional[int]
    owner_id: int
    name: str
    type: str
    location: str
    capacity: int
    price_per_hour: Decimal
    status: str = "pending"  # 'pending', 'verified', 'rejected', 'suspended'
    created_at: Optional[datetime] = None


@dataclass
class Event:
    id: Optional[int]
    owner_id: int
    name: str
    category: str
    event_date: date
    start_time: time
    end_time: time
    organizer_id: Optional[int] = None
    venue_id: Optional[int] = None
    description: Optional[str] = None
    expected_attendees: int = 0
    status: str = "draft"  # 'draft', 'planned', 'confirmed', 'live', 'completed', 'cancelled'
    live_status: str = "upcoming"  # 'upcoming', 'in_progress', 'delayed', 'completed', 'cancelled'
    created_at: Optional[datetime] = None


@dataclass
class EventScheduleItem:
    id: Optional[int]
    event_id: int
    title: str
    start_time: time
    end_time: time
    created_at: Optional[datetime] = None


# ==============================================================================
# 3. VENDOR SERVICES & AVAILABILITY
# ==============================================================================

@dataclass
class VendorService:
    id: Optional[int]
    vendor_id: int
    name: str
    price: Decimal
    description: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class VendorAvailability:
    id: Optional[int]
    vendor_id: int
    date: date
    start_time: time
    end_time: time
    created_at: Optional[datetime] = None


# ==============================================================================
# 4. BOOKINGS
# ==============================================================================

@dataclass
class Booking:
    id: Optional[int]
    event_id: int
    booking_type: str  # 'venue', 'vendor', 'delivery'
    booking_date: date
    start_time: time
    end_time: time
    venue_id: Optional[int] = None
    vendor_id: Optional[int] = None
    service_id: Optional[int] = None
    amount: Decimal = Decimal("0.00")
    status: str = "pending"  # 'pending', 'requested', 'confirmed', 'rejected', 'cancelled'
    payment_status: str = "payment_pending"  # 'payment_pending', 'partially_paid', 'paid'
    commission_amount: Decimal = Decimal("0.00")
    created_at: Optional[datetime] = None


# ==============================================================================
# 5. BUDGETS & EXPENSES (Remaining amount is computed, not stored)
# ==============================================================================

@dataclass
class BudgetItem:
    id: Optional[int]
    budget_id: int
    category: str
    allocated_amount: Decimal
    spent_amount: Decimal = Decimal("0.00")
    created_at: Optional[datetime] = None

    @property
    def remaining_amount(self) -> Decimal:
        """Computed remaining amount."""
        return self.allocated_amount - self.spent_amount

    @property
    def is_over_budget(self) -> bool:
        """Flag when spent exceeds allocation."""
        return self.spent_amount > self.allocated_amount


@dataclass
class Budget:
    id: Optional[int]
    event_id: int
    total_amount: Decimal
    items: List[BudgetItem] = field(default_factory=list)
    created_at: Optional[datetime] = None

    @property
    def total_allocated(self) -> Decimal:
        return sum((item.allocated_amount for item in self.items), Decimal("0.00"))

    @property
    def total_spent(self) -> Decimal:
        return sum((item.spent_amount for item in self.items), Decimal("0.00"))

    @property
    def total_remaining(self) -> Decimal:
        return self.total_amount - self.total_spent


# ==============================================================================
# 6. PAYMENTS & INVOICES
# ==============================================================================

@dataclass
class Payment:
    id: Optional[int]
    booking_id: int
    amount: Decimal
    method: str  # 'upi', 'net_banking', 'card', 'cash', 'bank_transfer'
    status: str  # 'pending', 'success', 'failed', 'refunded'
    transaction_id: str
    paid_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


@dataclass
class Invoice:
    id: Optional[int]
    booking_id: int
    invoice_no: str
    tax: Decimal
    total: Decimal
    issued_at: Optional[datetime] = None


# ==============================================================================
# 7. ATTENDEES & NOTIFICATIONS
# ==============================================================================

@dataclass
class Attendee:
    id: Optional[int]
    event_id: int
    name: str
    email: str
    phone: Optional[str] = None
    invitation_status: str = "invited"  # 'invited', 'registered', 'declined'
    rsvp_status: str = "pending"  # 'pending', 'accepted', 'declined', 'maybe'
    checked_in_at: Optional[datetime] = None
    checked_out_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


@dataclass
class Notification:
    id: Optional[int]
    user_id: int
    message: str
    status: str = "unread"  # 'unread', 'read'
    created_at: Optional[datetime] = None


# ==============================================================================
# 8. DELIVERY TASKS
# ==============================================================================

@dataclass
class DeliveryTask:
    id: Optional[int]
    event_id: int
    pickup: str
    destination: str
    scheduled_at: datetime
    item_description: str
    partner_id: Optional[int] = None
    quantity: int = 1
    instructions: Optional[str] = None
    status: str = "assigned"  # 'assigned', 'accepted', 'pickup_pending', 'picked_up', 'in_transit', 'delivered', 'failed', 'cancelled'
    created_at: Optional[datetime] = None


# ==============================================================================
# 9. REVIEWS, CHAT & AUDIT LOGS
# ==============================================================================

@dataclass
class Review:
    id: Optional[int]
    booking_id: int
    reviewer_id: int
    vendor_id: int
    rating: int  # 1 to 5
    comment: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class ChatMessage:
    id: Optional[int]
    event_id: int
    sender_id: int
    receiver_id: int
    message: str
    sent_at: Optional[datetime] = None


@dataclass
class AuditLog:
    id: Optional[int]
    action: str
    entity: str
    user_id: Optional[int] = None
    entity_id: Optional[int] = None
    result: str = "success"  # 'success', 'failure', 'denied'
    created_at: Optional[datetime] = None
