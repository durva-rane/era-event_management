"""Opt-in service integration tests for vendor bookings, budgets, RSVP and delivery."""
from datetime import date, timedelta
import os
import uuid

import pytest

from core.config import Config
from core.db import get_db_connection
from core.errors import AuthorizationError, ConflictError
from modules.attendees import services as attendee_services
from modules.delivery import services as delivery_services
from modules.finance import services as finance_services
from modules.vendors import services as vendor_services


TEST_DB = os.getenv("ERA_TEST_DB_NAME", "")
pytestmark = pytest.mark.skipif(not TEST_DB.startswith("era_test_"), reason="Set ERA_TEST_DB_NAME to an isolated migrated era_test_* MySQL database")


@pytest.fixture
def workflow_records(monkeypatch):
    monkeypatch.setattr(Config, "DB_NAME", TEST_DB)
    # Keep integration tests isolated from external notification providers.
    monkeypatch.setattr(attendee_services, "notify_in_transaction", lambda *args, **kwargs: None)
    monkeypatch.setattr(vendor_services, "notify_in_transaction", lambda *args, **kwargs: None)
    monkeypatch.setattr(finance_services, "notify_in_transaction", lambda *args, **kwargs: None)
    monkeypatch.setattr(delivery_services, "notify_in_transaction", lambda *args, **kwargs: None)
    suffix = uuid.uuid4().hex[:10]
    conn = get_db_connection(); cur = conn.cursor()
    ids = {}
    try:
        for key, role, phone in (("client", "client", "9"), ("organizer", "organizer", "8"), ("vendor", "vendor", "7"), ("partner", "delivery_partner", "6")):
            cur.execute("INSERT INTO users(name,email,phone,password_hash,role,status) VALUES(%s,%s,%s,'integration-test',%s,'active')", (key.title(), f"{key}-{suffix}@test.invalid", phone + suffix[:9], role))
            ids[key] = cur.lastrowid
        cur.execute("INSERT INTO vendors(user_id,business_name,service_type,pricing,location,verification_status) VALUES(%s,'Test Catering','catering',100,'Test City','verified')", (ids["vendor"],))
        cur.execute("INSERT INTO vendor_services(vendor_id,name,price) VALUES(%s,'Test package',100)", (ids["vendor"],)); ids["service"] = cur.lastrowid
        day = date.today() + timedelta(days=60); ids["day"] = day
        cur.execute("INSERT INTO vendor_availability(vendor_id,date,start_time,end_time) VALUES(%s,%s,'09:00:00','18:00:00')", (ids["vendor"], day))
        cur.execute("INSERT INTO delivery_partners(user_id,availability,status) VALUES(%s,'available','active')", (ids["partner"],))
        cur.execute("INSERT INTO events(owner_id,organizer_id,name,category,event_date,start_time,end_time,expected_attendees,status) VALUES(%s,%s,'Integration event','wedding',%s,'10:00:00','12:00:00',30,'planned')", (ids["client"], ids["organizer"], day)); ids["event"] = cur.lastrowid
        cur.execute("INSERT INTO budgets(event_id,total_amount) VALUES(%s,1000)", (ids["event"],)); ids["budget"] = cur.lastrowid
        cur.execute("INSERT INTO budget_items(budget_id,category,allocated_amount,estimated_amount) VALUES(%s,'catering',1000,300)", (ids["budget"],))
        conn.commit()
    finally:
        cur.close(); conn.close()
    try:
        yield ids
    finally:
        conn = get_db_connection(); cur = conn.cursor()
        try:
            cur.execute("DELETE FROM users WHERE id IN (%s,%s,%s,%s)", (ids["client"],ids["organizer"],ids["vendor"],ids["partner"]))
            conn.commit()
        finally:
            cur.close(); conn.close()


def test_vendor_request_acceptance_confirms_booking_and_commission(workflow_records):
    ids = workflow_records
    booking_id = vendor_services.create_booking(ids["client"], "client", ids["event"], {"vendor_id": ids["vendor"], "service_id": ids["service"], "quantity": 2})
    result = vendor_services.respond_booking(ids["vendor"], booking_id, "accepted")
    assert result["status"] == "confirmed"
    assert str(result["commission_amount"]) == "10.00"
    conn = get_db_connection(); cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT status,commission_amount FROM bookings WHERE id=%s", (booking_id,))
        row = cur.fetchone()
        assert row["status"] == "confirmed"
        assert float(row["commission_amount"]) == pytest.approx(10.0)
    finally:
        cur.close(); conn.close()


def test_budget_rollup_counts_confirmed_bookings_and_successful_payments(workflow_records):
    ids = workflow_records
    conn = get_db_connection(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO bookings(event_id,booking_type,vendor_id,service_id,booking_date,start_time,end_time,amount,status,budget_category) VALUES(%s,'vendor',%s,%s,%s,'10:00:00','11:00:00',200,'confirmed','catering')", (ids["event"],ids["vendor"],ids["service"],ids["day"]))
        booking_id=cur.lastrowid
        cur.execute("INSERT INTO payments(booking_id,amount,method,status,transaction_id,record_type) VALUES(%s,25,'mock','success',%s,'charge')", (booking_id,"test-"+uuid.uuid4().hex))
        conn.commit()
    finally:
        cur.close(); conn.close()
    summary=finance_services.budget_summary(ids["client"],"client",ids["event"])
    assert summary["allocated"] == 1000
    assert summary["spent"] == 225
    assert summary["remaining"] == 775


def test_public_rsvp_token_records_decline(workflow_records):
    ids=workflow_records; token=uuid.uuid4().hex+uuid.uuid4().hex
    conn=get_db_connection(); cur=conn.cursor()
    try:
        cur.execute("INSERT INTO attendees(event_id,name,email,rsvp_token) VALUES(%s,'Guest',%s,%s)",(ids["event"],"guest-"+uuid.uuid4().hex+"@test.invalid",token))
        attendee_id=cur.lastrowid; conn.commit()
    finally:
        cur.close(); conn.close()
    result=attendee_services.submit_rsvp(token,"declined")
    assert result["status"] == "declined"
    conn=get_db_connection(); cur=conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT rsvp_status,invitation_status FROM attendees WHERE id=%s",(attendee_id,))
        assert cur.fetchone() == {"rsvp_status":"declined","invitation_status":"declined"}
    finally:
        cur.close(); conn.close()


def test_delivery_status_progression_and_invalid_skip(workflow_records):
    ids=workflow_records
    conn=get_db_connection(); cur=conn.cursor()
    try:
        cur.execute("INSERT INTO delivery_tasks(event_id,partner_id,pickup,destination,scheduled_at,item_description,quantity,status) VALUES(%s,%s,'A','B',NOW(),'Box',1,'assigned')",(ids["event"],ids["partner"]))
        task_id=cur.lastrowid; conn.commit()
    finally:
        cur.close(); conn.close()
    with pytest.raises(ConflictError): delivery_services.update_status(task_id,ids["partner"],"delivery_partner","delivered")
    for status in ("accepted","pickup_pending","picked_up","in_transit","delivered"):
        assert delivery_services.update_status(task_id,ids["partner"],"delivery_partner",status) == status


def test_event_service_rbac_rejects_unassigned_user(workflow_records):
    ids=workflow_records
    with pytest.raises(AuthorizationError):
        vendor_services.event_messages(ids["partner"],"delivery_partner",ids["event"])
