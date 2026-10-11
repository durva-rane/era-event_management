"""Opt-in InnoDB integration coverage; requires an isolated migrated era_test_* DB."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
import os
import threading
import uuid

import pytest

from core.config import Config
from core.errors import ConflictError
from core.db import get_db_connection
from modules.events.services import save_event


TEST_DB = os.getenv("ERA_TEST_DB_NAME", "")
pytestmark = pytest.mark.skipif(not TEST_DB.startswith("era_test_"), reason="Set ERA_TEST_DB_NAME to an isolated migrated era_test_* MySQL database")


def test_two_concurrent_event_saves_cannot_double_book_a_venue(monkeypatch):
    monkeypatch.setattr(Config, "DB_NAME", TEST_DB)
    monkeypatch.setattr("core.notification_service._dispatch", lambda *args, **kwargs: None)
    suffix = uuid.uuid4().hex[:12]
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO users(name,email,phone,password_hash,role,status) VALUES(%s,%s,%s,'test','client','active')", ("Test client",f"{suffix}@test.invalid",f"9{suffix[:9]}"))
        owner_id = cur.lastrowid
        cur.execute("INSERT INTO users(name,email,phone,password_hash,role,status) VALUES(%s,%s,%s,'test','venue_owner','active')", ("Test owner",f"owner-{suffix}@test.invalid",f"8{suffix[:9]}"))
        venue_owner_id = cur.lastrowid
        cur.execute("INSERT INTO venues(owner_id,name,type,location,capacity,price_per_hour,status) VALUES(%s,'Concurrency venue','Hall','Test',100,100,'verified')", (venue_owner_id,))
        venue_id = cur.lastrowid
        conn.commit()
    finally:
        cur.close(); conn.close()

    barrier = threading.Barrier(2)
    day = (date.today() + timedelta(days=35)).isoformat()
    payloads = [
        {"name": f"Concurrent {suffix}-{i}", "category": "Test", "event_date": day, "start_time": "10:00", "end_time": "12:00", "expected_attendees": 50, "venue_id": venue_id}
        for i in range(2)
    ]

    def attempt(payload):
        barrier.wait(timeout=5)
        try:
            return save_event(owner_id, "client", payload)
        except ConflictError:
            return "conflict"

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, payloads))
        assert sum(result != "conflict" for result in results) == 1
        assert results.count("conflict") == 1
    finally:
        cleanup = get_db_connection(); c = cleanup.cursor()
        try:
            c.execute("DELETE FROM users WHERE id IN (%s,%s)", (owner_id, venue_owner_id)); cleanup.commit()
        finally:
            c.close(); cleanup.close()
