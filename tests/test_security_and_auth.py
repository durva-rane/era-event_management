from flask import jsonify

from core.decorators import role_required
from modules.auth.routes import _safe_next
from modules.auth.services import AuthService


def test_csrf_rejects_unsafe_request_without_token(client):
    response = client.post("/api/register", json={})
    assert response.status_code == 400
    assert "CSRF" in response.get_json()["message"]


def test_csrf_cookie_token_allows_unsafe_request(client):
    client.get("/login")
    token = client.get_cookie("era_csrf_token").value
    response = client.post("/api/register", json={}, headers={"X-CSRF-Token": token})
    assert "CSRF" not in response.get_json().get("message", "")


def test_login_return_target_rejects_external_origin(app):
    with app.test_request_context("/login?next=https://attacker.example"):
        assert _safe_next("https://attacker.example/path") == "/dashboard"


def test_auth_login_creates_role_session_and_rejects_external_next(client, monkeypatch):
    client.get("/login")
    token = client.get_cookie("era_csrf_token").value
    monkeypatch.setattr(AuthService, "authenticate_user", lambda **kwargs: {
        "id": 12, "name": "Client", "email": "client@example.test", "phone": "123", "role": "client", "status": "active"
    })
    response = client.post("/api/login?next=https://attacker.example", json={"identifier": "client@example.test", "password": "secret"}, headers={"X-CSRF-Token": token})
    assert response.status_code == 200
    assert response.get_json()["redirect_url"] == "/dashboard"
    with client.session_transaction() as session:
        assert session["user_id"] == 12
        assert session["user_role"] == "client"


def test_role_guard_denies_wrong_role(app, client):
    @app.get("/api/test/vendor-only")
    @role_required("vendor")
    def vendor_only():
        return jsonify(success=True)

    with client.session_transaction() as session:
        session.update(user_id=42, user_role="client", last_active=9999999999)
    response = client.get("/api/test/vendor-only")
    assert response.status_code == 403


def test_get_logout_does_not_change_session(client):
    with client.session_transaction() as session:
        session.update(user_id=91, user_role="client")
    response = client.get("/logout", follow_redirects=False)
    assert response.status_code in (302, 404)
    with client.session_transaction() as session:
        assert session.get("user_id") == 91


def test_unexpected_api_error_does_not_leak_exception_detail(app, client):
    @app.get("/api/test/raises")
    def raises():
        raise RuntimeError("password=super-secret")
    response = client.get("/api/test/raises")
    assert response.status_code == 500
    assert "super-secret" not in response.get_data(as_text=True)
