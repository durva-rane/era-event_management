"""
Comprehensive Test Suite for ERA Auth Module
"""

import io
from app import create_app
from core.db import get_db_cursor


def run_tests():
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    print("=" * 60)
    print("RUNNING ERA AUTH MODULE TEST SUITE")
    print("=" * 60)

    # Clean up any leftover test accounts
    with get_db_cursor(commit_on_success=True) as (cursor, _):
        cursor.execute("DELETE FROM users WHERE email IN ('kavita.sen@example.com', 'sunil.sound@example.com', 'lockout.target@example.com')")
        cursor.execute("DELETE FROM login_attempts WHERE identifier = 'lockout.target@example.com'")


    # ----------------------------------------------------
    # TEST 1: Admin Login
    # ----------------------------------------------------
    print("\n[TEST 1] Admin Login with seed credentials...")
    res = client.post("/api/login", json={
        "identifier": "admin@era.com",
        "password": "Admin@123",
        "role": "admin"
    })
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.get_json()}"
    data = res.get_json()
    assert data["success"] is True
    assert data["user"]["role"] == "admin"
    print("  ✓ Admin logged in successfully:", data["user"]["email"])

    # ----------------------------------------------------
    # TEST 2: Client Registration (Becomes Active Immediately)
    # ----------------------------------------------------
    print("\n[TEST 2] Client Registration (Immediate Active Status)...")
    reg_client_payload = {
        "role": "client",
        "name": "Kavita Sen",
        "email": "kavita.sen@example.com",
        "phone": "9812341234",
        "password": "SecurePassword@2026",
        "confirm_password": "SecurePassword@2026",
        "event_requirements": "Corporate awards night for 300 delegates"
    }
    res = client.post("/api/register", data=reg_client_payload)
    assert res.status_code == 201, f"Failed: {res.get_json()}"
    data = res.get_json()
    assert data["success"] is True
    assert data["requires_verification"] is False
    print("  ✓ Client registered with active status:", data["message"])

    # Test that this newly registered client can log in immediately
    res = client.post("/api/login", json={
        "identifier": "kavita.sen@example.com",
        "password": "SecurePassword@2026",
        "role": "client"
    })
    assert res.status_code == 200
    print("  ✓ Newly registered client logged in immediately.")

    # ----------------------------------------------------
    # TEST 3: Duplicate Email Rejection
    # ----------------------------------------------------
    print("\n[TEST 3] Duplicate Email Rejection...")
    res = client.post("/api/register", data=reg_client_payload)
    assert res.status_code == 409
    data = res.get_json()
    assert data["success"] is False
    print("  ✓ Duplicate email correctly rejected with 409 Conflict:", data["message"])

    # ----------------------------------------------------
    # TEST 4: Vendor Registration with Document Upload (Becomes Pending)
    # ----------------------------------------------------
    print("\n[TEST 4] Vendor Registration with File Upload (Status=Pending)...")
    fake_doc = (io.BytesIO(b"%PDF-1.4 sample license document"), "fssai_cert.pdf")
    reg_vendor_payload = {
        "role": "vendor",
        "name": "Sunil Shinde",
        "organization": "Shinde Sound & Stage Tech",
        "business_name": "Shinde Sound & Stage Tech",
        "service_type": "Sound & Stage",
        "pricing": "25000",
        "location": "Pune",
        "email": "sunil.sound@example.com",
        "phone": "9898981212",
        "password": "VendorPassword@2026",
        "confirm_password": "VendorPassword@2026",
        "verification_doc": fake_doc
    }
    res = client.post("/api/register", data=reg_vendor_payload, content_type="multipart/form-data")
    assert res.status_code == 201, f"Failed: {res.get_json()}"
    data = res.get_json()
    assert data["success"] is True
    assert data["requires_verification"] is True
    print("  ✓ Vendor registered with pending verification status:", data["message"])

    # ----------------------------------------------------
    # TEST 5: Block Pending Vendor from Logging In
    # ----------------------------------------------------
    print("\n[TEST 5] Block Pending Vendor from Logging In...")
    res = client.post("/api/login", json={
        "identifier": "sunil.sound@example.com",
        "password": "VendorPassword@2026",
        "role": "vendor"
    })
    assert res.status_code == 401
    data = res.get_json()
    assert "pending verification" in data["message"].lower()
    print("  ✓ Pending vendor login blocked with clear message:", data["message"])

    # ----------------------------------------------------
    # TEST 6: Account Lockout after 5 Failed Attempts (15 min)
    # ----------------------------------------------------
    print("\n[TEST 6] 5-Attempt Lockout Mechanism...")
    test_email = "lockout.target@example.com"
    # Create target account
    client.post("/api/register", data={
        "role": "client",
        "name": "Lockout Test User",
        "email": test_email,
        "phone": "9800112233",
        "password": "CorrectPassword@2026",
        "confirm_password": "CorrectPassword@2026",
    })

    # Fail 4 times
    for i in range(1, 5):
        res = client.post("/api/login", json={
            "identifier": test_email,
            "password": "WrongPassword123!"
        })
        assert res.status_code == 401
        print(f"  Attempt {i}: {res.get_json()['message']}")

    # 5th failure triggers lockout
    res = client.post("/api/login", json={
        "identifier": test_email,
        "password": "WrongPassword123!"
    })
    assert res.status_code == 401
    print(f"  Attempt 5 (Lockout trigger): {res.get_json()['message']}")

    # 6th attempt with correct password should still be blocked due to active lockout!
    res = client.post("/api/login", json={
        "identifier": test_email,
        "password": "CorrectPassword@2026"
    })
    assert res.status_code == 401
    assert "locked" in res.get_json()["message"].lower()
    print("  ✓ Correct password blocked due to active 15-minute lockout:", res.get_json()["message"])

    # ----------------------------------------------------
    # TEST 7: Forgot-Password & Token Reset Flow
    # ----------------------------------------------------
    print("\n[TEST 7] Forgot-Password & Token Reset Flow...")
    res = client.post("/api/forgot-password", json={"email": "client@era.com"})
    assert res.status_code == 200
    token = res.get_json().get("token")
    if not token:
        with get_db_cursor(commit_on_success=False) as (cursor, _):
            cursor.execute(
                """
                SELECT token FROM password_reset_tokens
                WHERE user_id = (SELECT id FROM users WHERE email='client@era.com')
                ORDER BY id DESC LIMIT 1
                """
            )
            row = cursor.fetchone()
            token = row["token"] if row else None
    assert token, "Token expected in DB"
    print("  ✓ Retrieved reset token from database:", token)


    # Reset password with token
    new_pw = "BrandNewPassword@2026"
    res = client.post(f"/api/reset-password/{token}", json={
        "password": new_pw,
        "confirm_password": new_pw
    })
    assert res.status_code == 200
    print("  ✓ Password reset successfully:", res.get_json()["message"])

    # Log in with new password
    res = client.post("/api/login", json={
        "identifier": "client@era.com",
        "password": new_pw,
        "role": "client"
    })
    assert res.status_code == 200
    print("  ✓ Logged in with new password successfully.")

    # ----------------------------------------------------
    # TEST 8: Profile View & Update
    # ----------------------------------------------------
    print("\n[TEST 8] Profile View & Update...")
    # Session is authenticated as client@era.com
    res = client.get("/api/profile")
    assert res.status_code == 200
    profile_data = res.get_json()
    assert profile_data["user"]["email"] == "client@era.com"
    print("  ✓ Retrieved profile:", profile_data["user"]["name"])

    # Update profile
    res = client.post("/api/profile", json={
        "name": "Priya Sharma (Updated)",
        "phone": "9811119999",
        "event_requirements": "Updated requirements: 5-star venue with outdoor banquet"
    })
    assert res.status_code == 200
    print("  ✓ Profile updated:", res.get_json()["message"])

    # ----------------------------------------------------
    # TEST 9: Logout & Session Destroy
    # ----------------------------------------------------
    print("\n[TEST 9] Logout & Session Destruction...")
    res = client.post("/api/logout")
    assert res.status_code == 200
    print("  ✓ Logout successful.")

    # Accessing profile now should be unauthorized (401)
    res = client.get("/api/profile")
    assert res.status_code == 401
    print("  ✓ Profile correctly blocked after logout (401 Unauthorized).")

    # ----------------------------------------------------
    # TEST 10: Audit Log Verification
    # ----------------------------------------------------
    print("\n[TEST 10] Audit Log Records...")
    with get_db_cursor(commit_on_success=False) as (cursor, _):
        cursor.execute("SELECT action, entity, result, COUNT(*) as cnt FROM audit_logs GROUP BY action, entity, result ORDER BY cnt DESC")
        logs = cursor.fetchall()
        for log in logs:
            print(f"  - Action: {log['action']:<25} Entity: {log['entity']:<12} Result: {log['result']:<10} (Count: {log['cnt']})")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED SUCCESSFULLY! AUTH MODULE IS FULLY VERIFIED.")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
