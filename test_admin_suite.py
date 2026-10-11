"""
Comprehensive Test Suite for ERA Admin Module
"""

from app import create_app
from core.db import get_db_cursor


def run_admin_tests():
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    print("=" * 60)
    print("RUNNING ERA ADMIN MODULE TEST SUITE")
    print("=" * 60)

    # ----------------------------------------------------
    # TEST 1: Role-Based Access Control (Admin-Only)
    # ----------------------------------------------------
    print("\n[TEST 1] RBAC Protection on Admin Routes...")
    # Unauthenticated
    res = client.get("/api/admin/metrics")
    assert res.status_code == 401, f"Expected 401, got {res.status_code}"
    print("  ✓ Unauthenticated access correctly blocked (401).")

    # Log in as Client
    res = client.post("/api/login", json={
        "identifier": "client@era.com",
        "password": "User@123",
        "role": "client"
    })
    assert res.status_code == 200

    # Client tries to access admin API
    res = client.get("/api/admin/metrics")
    assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}"
    print("  ✓ Client role access to admin correctly blocked (403 Forbidden).")

    # Log out client
    client.post("/api/logout")

    # Log in as Admin
    res = client.post("/api/login", json={
        "identifier": "admin@era.com",
        "password": "Admin@123",
        "role": "admin"
    })
    assert res.status_code == 200
    print("  ✓ Administrator logged in successfully.")

    # ----------------------------------------------------
    # TEST 2: Admin Dashboard Metrics & Counts
    # ----------------------------------------------------
    print("\n[TEST 2] Admin Dashboard Metrics & Activity...")
    res = client.get("/api/admin/metrics")
    assert res.status_code == 200
    metrics = res.get_json()["metrics"]
    assert "total_users" in metrics
    assert "pending_verifications" in metrics
    assert "total_events" in metrics
    assert "total_bookings" in metrics
    assert "total_revenue" in metrics
    assert len(metrics["recent_activity"]) > 0
    print(f"  ✓ Metrics: Total Users={metrics['total_users']}, Events={metrics['total_events']}, Bookings={metrics['total_bookings']}, Revenue=₹{metrics['total_revenue']:,.2f}")

    # Test HTML dashboard page
    res = client.get("/admin/dashboard")
    assert res.status_code == 200
    print("  ✓ Admin HTML dashboard loaded successfully.")

    # ----------------------------------------------------
    # TEST 3: User Management (List, Filter, Status, Role, Reset)
    # ----------------------------------------------------
    print("\n[TEST 3] User Management Operations...")
    res = client.get("/api/admin/users?role=vendor")
    assert res.status_code == 200
    vendors = res.get_json()["users"]
    assert len(vendors) > 0
    target_user_id = vendors[0]["id"]
    print(f"  ✓ Retrieved {len(vendors)} vendor users. Target User ID: #{target_user_id}")

    # Change user status to suspended
    res = client.post(f"/api/admin/users/{target_user_id}/status", json={"status": "suspended"})
    assert res.status_code == 200
    print(f"  ✓ User #{target_user_id} suspended: {res.get_json()['message']}")

    # Change user status back to active
    res = client.post(f"/api/admin/users/{target_user_id}/status", json={"status": "active"})
    assert res.status_code == 200
    print(f"  ✓ User #{target_user_id} activated: {res.get_json()['message']}")

    # Reset user access (clears lockout & sets temporary password)
    res = client.post(f"/api/admin/users/{target_user_id}/reset-access", json={"temporary_password": "TempPassword@2026"})
    assert res.status_code == 200
    print(f"  ✓ User #{target_user_id} access reset: {res.get_json()['message']}")

    # ----------------------------------------------------
    # TEST 4: Verification Queue (Approve with Remarks & Notification)
    # ----------------------------------------------------
    print("\n[TEST 4] Verification Queue & Decision Processing...")
    res = client.get("/api/admin/verifications")
    assert res.status_code == 200
    queue = res.get_json()["queue"]
    assert len(queue) > 0, "Expected at least 1 document in queue"
    target_doc = queue[0]
    doc_id = target_doc["doc_id"]
    doc_user_id = target_doc["user_id"]
    print(f"  ✓ Found document #{doc_id} for user #{doc_user_id} ({target_doc['user_name']})")

    # Approve verification with remarks
    res = client.post(f"/api/admin/verifications/{doc_id}/decision", json={
        "decision": "approve",
        "remarks": "FSSAI and corporate GST verified with municipal authorities."
    })
    assert res.status_code == 200
    print(f"  ✓ Verification approved: {res.get_json()['message']}")

    # Verify that in-app notification was sent to user through shared hook
    with get_db_cursor(commit_on_success=False) as (cursor, _):
        cursor.execute("SELECT * FROM notifications WHERE user_id = %s ORDER BY id DESC LIMIT 1", (doc_user_id,))
        notif = cursor.fetchone()
        assert notif is not None, "Notification must be created"
        assert "verified" in notif["message"].lower() or "approved" in notif["message"].lower()
        print(f"  ✓ Verified notification sent to User #{doc_user_id}: '{notif['message']}'")

        # Verify audit log was recorded for VERIFY_APPROVE
        cursor.execute("SELECT * FROM audit_logs WHERE action = 'VERIFY_APPROVE' AND entity_id = %s LIMIT 1", (doc_id,))
        audit = cursor.fetchone()
        assert audit is not None, "Audit log must be recorded"
        print(f"  ✓ Audit log verified: Action={audit['action']}, Actor User ID={audit['user_id']}")

    # ----------------------------------------------------
    # TEST 5: Venues & Bookings Management
    # ----------------------------------------------------
    print("\n[TEST 5] Venues & Bookings Console...")
    res = client.get("/admin/venues")
    assert res.status_code == 200

    # Update venue status to verified
    res = client.post("/api/admin/venues/1/status", json={"status": "verified"})
    assert res.status_code == 200
    print("  ✓ Venue #1 status updated to 'verified'")

    # Update booking status to confirmed
    res = client.post("/api/admin/bookings/1/status", json={"status": "confirmed"})
    assert res.status_code == 200
    print("  ✓ Booking #1 status updated to 'confirmed'")

    # ----------------------------------------------------
    # TEST 6: Payments Overview
    # ----------------------------------------------------
    print("\n[TEST 6] Payments Overview...")
    res = client.get("/api/admin/payments")
    assert res.status_code == 200
    payments = res.get_json()["payments"]
    assert len(payments) > 0
    print(f"  ✓ Retrieved {len(payments)} payment transactions. Sample Txn ID: {payments[0]['transaction_id']}, Amount: ₹{float(payments[0]['amount']):,.2f}")


    # ----------------------------------------------------
    # TEST 7: Audit Log Viewer with Filters
    # ----------------------------------------------------
    print("\n[TEST 7] Audit Log Viewer with Filters...")
    res = client.get("/api/admin/audit-logs?action=VERIFY_APPROVE")
    assert res.status_code == 200
    filtered_logs = res.get_json()["logs"]
    assert len(filtered_logs) > 0
    assert all(l["action"] == "VERIFY_APPROVE" for l in filtered_logs)
    print(f"  ✓ Filtered audit logs by action='VERIFY_APPROVE': found {len(filtered_logs)} records.")

    res = client.get("/admin/audit-logs")
    assert res.status_code == 200
    print("  ✓ Audit log HTML page loaded successfully.")

    print("\n" + "=" * 60)
    print("ALL ADMIN MODULE TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    run_admin_tests()
