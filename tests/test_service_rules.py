from decimal import Decimal

import pytest

from core.errors import AuthorizationError, ConflictError
from modules.attendees.services import _invitation_status_for_rsvp
from modules.delivery.services import TRANSITIONS
from modules.events.services import _available_venue
from modules.finance.services import _budget_totals
from modules.vendors.services import _commission_amount
from modules.vendors.services import _event_access
from core.db import after_commit, get_db_cursor


class VenueCursor:
    def __init__(self, conflict=False, capacity=100):
        self.conflict = conflict
        self.capacity = capacity
        self.statements = []
        self.row = None

    def execute(self, sql, params=()):
        self.statements.append((sql, params))
        if "FROM venues" in sql:
            self.row = {"id": 3, "capacity": self.capacity, "status": "verified"}
        else:
            self.row = {"id": 8} if self.conflict else None

    def fetchone(self):
        return self.row


def test_venue_overlap_uses_strict_interval_predicate_and_row_lock():
    cursor = VenueCursor(conflict=True)
    result = _available_venue(cursor, 3, "2030-01-01", "10:00", "11:00", 40)
    assert result is None
    assert "FOR UPDATE" in cursor.statements[0][0]
    assert "start_time < %s AND end_time > %s" in cursor.statements[1][0]


def test_venue_capacity_is_enforced_before_booking_insert():
    with pytest.raises(ConflictError, match="capacity"):
        _available_venue(VenueCursor(capacity=20), 3, "2030-01-01", "10:00", "11:00", 40)


def test_vendor_booking_commission_uses_configured_percent():
    assert _commission_amount(Decimal("199.99")) == Decimal("10.00")


def test_budget_rollup_math_includes_booking_and_payment_totals():
    class Cursor:
        rows = [
            {"allocated": Decimal("1000"), "item_estimate": Decimal("750")},
            {"total_amount": Decimal("1000")},
            {"estimate": Decimal("100")},
            {"spent": Decimal("500")},
            {"paid": Decimal("120")},
        ]
        def execute(self, *_): pass
        def fetchone(self): return self.rows.pop(0)
    result = _budget_totals(Cursor(), 7)
    assert result["allocated"] == Decimal("1000")
    assert result["estimated"] == Decimal("850")
    assert result["spent"] == Decimal("620")
    assert result["remaining"] == result["variance"] == Decimal("380")


@pytest.mark.parametrize("status,expected", [("accepted", "registered"), ("declined", "declined"), ("maybe", "invited")])
def test_rsvp_status_mapping(status, expected):
    assert _invitation_status_for_rsvp(status) == expected


def test_delivery_transition_graph_rejects_skipped_steps():
    assert "accepted" in TRANSITIONS["assigned"]
    assert "delivered" not in TRANSITIONS["assigned"]
    assert "delivered" in TRANSITIONS["in_transit"]
    assert not TRANSITIONS["delivered"]


def test_event_rbac_rejects_client_who_does_not_own_event():
    with pytest.raises(AuthorizationError):
        _event_access({"owner_id": 7, "organizer_id": 8}, 9, "client")


def test_transaction_runs_registered_side_effect_after_commit(monkeypatch):
    class Connection:
        def cursor(self, dictionary=True): return object()
        def commit(self): events.append("commit")
        def rollback(self): events.append("rollback")
        def close(self): events.append("close")
    events=[]
    monkeypatch.setattr("core.db.get_db_connection", Connection)
    with get_db_cursor():
        assert after_commit(lambda: events.append("callback"))
        assert events == []
    assert events == ["commit", "close", "callback"]


def test_transaction_discards_side_effect_on_rollback(monkeypatch):
    class Connection:
        def cursor(self, dictionary=True): return object()
        def commit(self): events.append("commit")
        def rollback(self): events.append("rollback")
        def close(self): events.append("close")
    events=[]
    monkeypatch.setattr("core.db.get_db_connection", Connection)
    with pytest.raises(RuntimeError):
        with get_db_cursor():
            after_commit(lambda: events.append("callback"))
            raise RuntimeError("fail")
    assert events == ["rollback", "close"]
