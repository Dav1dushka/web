from sqlalchemy import select
from app.models import User


def register(client, email="david@example.com", password="correct-horse-battery"):
    return client.post("/auth/register", json={"email": email, "full_name": "Davyd Velychko", "password": password})


def login(client, email="david@example.com", password="correct-horse-battery"):
    return client.post("/auth/token", data={"username": email, "password": password})


def test_register_hashes_password_and_login_returns_tokens(client, client_and_db):
    response = register(client)
    assert response.status_code == 201
    assert response.json()["role"] == "user"
    with client_and_db[1]() as db:
        user = db.scalar(select(User).where(User.email == "david@example.com"))
        assert user.password_hash != "correct-horse-battery"
        assert user.password_hash.startswith("$argon2id$")
    tokens = login(client)
    assert tokens.status_code == 200
    assert tokens.json()["token_type"] == "bearer"
    assert tokens.json()["expires_in"] == 900
    assert tokens.json()["access_token"] and tokens.json()["refresh_token"]


def test_duplicate_email_is_rejected(client):
    assert register(client).status_code == 201
    assert register(client).status_code == 409


def test_password_minimum_length(client):
    response = client.post("/auth/register", json={"email": "short@example.com", "full_name": "Short User", "password": "short"})
    assert response.status_code == 422


def test_wrong_password_is_rejected(client):
    register(client)
    assert login(client, password="wrong-password-value").status_code == 401


def test_profile_requires_access_token(client):
    register(client)
    assert client.get("/users/me").status_code == 401
    tokens = login(client).json()
    response = client.get("/users/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert response.status_code == 200
    assert response.json()["email"] == "david@example.com"


def test_refresh_rotation_and_reuse_detection(client):
    register(client)
    tokens = login(client).json()
    rotated = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert rotated.status_code == 200
    new_pair = rotated.json()
    assert new_pair["refresh_token"] != tokens["refresh_token"]
    replay = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert replay.status_code == 401
    family_revoked = client.post("/auth/refresh", json={"refresh_token": new_pair["refresh_token"]})
    assert family_revoked.status_code == 401


def test_logout_revokes_refresh_token(client):
    register(client)
    tokens = login(client).json()
    response = client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]}, headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert response.status_code == 200
    assert client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401


def test_admin_routes_enforce_rbac_and_record_audit(client, client_and_db):
    register(client)
    register(client, "second@example.com")
    user_tokens = login(client).json()
    headers = {"Authorization": f"Bearer {user_tokens['access_token']}"}
    assert client.get("/admin/users", headers=headers).status_code == 403
    with client_and_db[1]() as db:
        user = db.scalar(select(User).where(User.email == "david@example.com"))
        user.role = "admin"
        db.commit()
    admin_tokens = login(client).json()
    admin_headers = {"Authorization": f"Bearer {admin_tokens['access_token']}"}
    listed = client.get("/admin/users", headers=admin_headers)
    second = next(item for item in listed.json() if item["email"] == "second@example.com")
    changed = client.patch(f"/admin/users/{second['id']}/role", json={"role": "admin"}, headers=admin_headers)
    assert changed.status_code == 200 and changed.json()["role"] == "admin"
    audit = client.get("/admin/audit", headers=admin_headers)
    assert audit.status_code == 200
    assert any(item["action"] == "admin.role_changed" for item in audit.json())


def test_last_admin_cannot_be_demoted_or_self_deactivated(client, client_and_db):
    register(client)
    with client_and_db[1]() as db:
        user = db.scalar(select(User).where(User.email == "david@example.com"))
        user.role = "admin"
        db.commit()
    tokens = login(client).json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    user_id = client.get("/users/me", headers=headers).json()["id"]
    assert client.patch(f"/admin/users/{user_id}/role", json={"role": "user"}, headers=headers).status_code == 409
    assert client.patch(f"/admin/users/{user_id}/status", json={"is_active": False}, headers=headers).status_code == 409
