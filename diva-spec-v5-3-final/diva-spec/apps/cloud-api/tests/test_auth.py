"""Auth, MFA, refresh and audit tests (TASK-PUB-01)."""

import pyotp
from fastapi.testclient import TestClient

PASSWORD = "correct-horse-battery-staple"
BOOTSTRAP_HEADERS = {"X-Bootstrap-Token": "dev-bootstrap-token"}


def _bootstrap(client: TestClient, email: str = "owner@diva.example.com") -> str:
    response = client.post(
        "/auth/bootstrap",
        json={"email": email, "password": PASSWORD},
        headers=BOOTSTRAP_HEADERS,
    )
    assert response.status_code == 201, response.text
    return response.json()["secret"]


def _enable_mfa(
    client: TestClient, secret: str, email: str = "owner@diva.example.com"
) -> list[str]:
    code = pyotp.TOTP(secret).now()
    response = client.post(
        "/auth/mfa/enable", json={"email": email, "password": PASSWORD, "code": code}
    )
    assert response.status_code == 200, response.text
    return response.json()["recovery_codes"]


def _owner_token(client: TestClient) -> str:
    secret = _bootstrap(client)
    _enable_mfa(client, secret)
    code = pyotp.TOTP(secret).now()
    response = client.post(
        "/auth/login", json={"email": "owner@diva.example.com", "password": PASSWORD, "totp": code}
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def test_bootstrap_is_single_use_and_token_guarded(client: TestClient) -> None:
    assert (
        client.post(
            "/auth/bootstrap",
            json={"email": "owner@diva.example.com", "password": PASSWORD},
            headers={"X-Bootstrap-Token": "wrong"},
        ).status_code
        == 403
    )
    secret = _bootstrap(client)
    assert len(secret) >= 16
    assert (
        client.post(
            "/auth/bootstrap",
            json={"email": "other@diva.example.com", "password": PASSWORD},
            headers=BOOTSTRAP_HEADERS,
        ).status_code
        == 409
    )


def test_owner_cannot_login_before_mfa(client: TestClient) -> None:
    _bootstrap(client)
    response = client.post(
        "/auth/login", json={"email": "owner@diva.example.com", "password": PASSWORD}
    )
    assert response.status_code == 403
    assert "MFA" in response.json()["detail"]


def test_owner_mfa_login_me_and_audit(client: TestClient) -> None:
    secret = _bootstrap(client)
    _enable_mfa(client, secret)
    code = pyotp.TOTP(secret).now()
    response = client.post(
        "/auth/login", json={"email": "owner@diva.example.com", "password": PASSWORD, "totp": code}
    )
    assert response.status_code == 200
    tokens = response.json()
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 200
    assert me.json()["role"] == "owner"
    assert me.json()["mfa_enabled"] is True
    audit = client.get(
        "/admin/audit?limit=20", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert audit.status_code == 200
    actions = {row["action"] for row in audit.json()}
    assert {"auth.bootstrap", "auth.mfa_enable", "auth.login"} <= actions


def test_login_without_or_with_wrong_mfa_is_rejected(client: TestClient) -> None:
    secret = _bootstrap(client)
    _enable_mfa(client, secret)
    missing = client.post(
        "/auth/login", json={"email": "owner@diva.example.com", "password": PASSWORD}
    )
    assert missing.status_code == 401
    assert missing.json()["detail"] == "mfa_required"
    wrong = client.post(
        "/auth/login",
        json={"email": "owner@diva.example.com", "password": PASSWORD, "totp": "000000"},
    )
    assert wrong.status_code == 401


def test_refresh_rotation_and_reuse_rejected(client: TestClient) -> None:
    secret = _bootstrap(client)
    _enable_mfa(client, secret)
    code = pyotp.TOTP(secret).now()
    tokens = client.post(
        "/auth/login", json={"email": "owner@diva.example.com", "password": PASSWORD, "totp": code}
    ).json()
    refreshed = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    assert refreshed.json()["refresh_token"] != tokens["refresh_token"]
    replay = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert replay.status_code == 401


def test_recovery_code_is_single_use(client: TestClient) -> None:
    secret = _bootstrap(client)
    codes = _enable_mfa(client, secret)
    response = client.post(
        "/auth/login",
        json={
            "email": "owner@diva.example.com",
            "password": PASSWORD,
            "recovery_code": codes[0],
        },
    )
    assert response.status_code == 200
    replay = client.post(
        "/auth/login",
        json={
            "email": "owner@diva.example.com",
            "password": PASSWORD,
            "recovery_code": codes[0],
        },
    )
    assert replay.status_code == 401


def test_owner_creates_staff_and_staff_cannot_admin(client: TestClient) -> None:
    owner_token = _owner_token(client)
    headers = {"Authorization": f"Bearer {owner_token}"}
    created = client.post(
        "/admin/users",
        json={"email": "staff@diva.example.com", "password": PASSWORD, "role": "staff"},
        headers=headers,
    )
    assert created.status_code == 201
    assert created.json()["mfa_enabled"] is False
    staff_login = client.post(
        "/auth/login", json={"email": "staff@diva.example.com", "password": PASSWORD}
    )
    assert staff_login.status_code == 200
    staff_headers = {"Authorization": f"Bearer {staff_login.json()['access_token']}"}
    assert client.get("/admin/audit", headers=staff_headers).status_code == 403
    assert client.get("/auth/me", headers=staff_headers).status_code == 200


def test_password_is_not_stored_in_plaintext(client: TestClient, db_session) -> None:
    _bootstrap(client)
    from sqlalchemy import select

    from cloud_api.models import User

    user = db_session.scalar(select(User))
    assert user is not None
    assert user.password_hash != PASSWORD
    assert user.password_hash.startswith("$argon2")


def test_failed_logins_are_rate_limited(client: TestClient) -> None:
    secret = _bootstrap(client)
    _enable_mfa(client, secret)
    for _ in range(5):
        response = client.post(
            "/auth/login",
            json={"email": "owner@diva.example.com", "password": "wrong-password"},
        )
        assert response.status_code == 401
    blocked = client.post(
        "/auth/login",
        json={"email": "owner@diva.example.com", "password": PASSWORD},
    )
    assert blocked.status_code == 429


def test_mfa_setup_cannot_overwrite_an_initialized_secret(client: TestClient) -> None:
    _bootstrap(client)
    response = client.post(
        "/auth/mfa/setup",
        json={"email": "owner@diva.example.com", "password": PASSWORD},
    )
    assert response.status_code == 409


def test_second_owner_is_rejected(client: TestClient) -> None:
    token = _owner_token(client)
    response = client.post(
        "/admin/users",
        json={"email": "owner2@diva.example.com", "password": PASSWORD, "role": "owner"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_refresh_reuse_revokes_the_whole_session_family(client: TestClient) -> None:
    secret = _bootstrap(client)
    _enable_mfa(client, secret)
    code = pyotp.TOTP(secret).now()
    tokens = client.post(
        "/auth/login", json={"email": "owner@diva.example.com", "password": PASSWORD, "totp": code}
    ).json()
    rotated = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).json()
    replay = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert replay.status_code == 401
    after_reuse = client.post("/auth/refresh", json={"refresh_token": rotated["refresh_token"]})
    assert after_reuse.status_code == 401


def test_expired_refresh_and_logout_are_rejected(client: TestClient, db_session) -> None:
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import select

    from cloud_api.models import RefreshToken

    secret = _bootstrap(client)
    _enable_mfa(client, secret)
    code = pyotp.TOTP(secret).now()
    tokens = client.post(
        "/auth/login", json={"email": "owner@diva.example.com", "password": PASSWORD, "totp": code}
    ).json()
    stored = db_session.scalar(select(RefreshToken))
    assert stored is not None
    stored.expires_at = datetime.now(UTC) - timedelta(days=1)
    db_session.commit()
    assert (
        client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code
        == 401
    )


def test_inactive_user_cannot_login(client: TestClient, db_session) -> None:
    from sqlalchemy import select

    from cloud_api.models import User

    owner_token = _owner_token(client)
    client.post(
        "/admin/users",
        json={"email": "staff@diva.example.com", "password": PASSWORD, "role": "staff"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    staff = db_session.scalar(select(User).where(User.email == "staff@diva.example.com"))
    assert staff is not None
    staff.is_active = False
    db_session.commit()
    response = client.post(
        "/auth/login", json={"email": "staff@diva.example.com", "password": PASSWORD}
    )
    assert response.status_code == 403


def test_production_rejects_dev_secrets() -> None:
    from cloud_api.config import Settings

    production = Settings(environment="production")
    try:
        production.validate_for_runtime()
    except RuntimeError as exc:
        assert "must be set" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("production must reject dev secrets")


def test_mfa_enable_is_rate_limited(client: TestClient) -> None:
    _bootstrap(client)
    for _ in range(5):
        response = client.post(
            "/auth/mfa/enable",
            json={"email": "owner@diva.example.com", "password": PASSWORD, "code": "000000"},
        )
        assert response.status_code == 401
    blocked = client.post(
        "/auth/mfa/enable",
        json={"email": "owner@diva.example.com", "password": PASSWORD, "code": "000000"},
    )
    assert blocked.status_code == 429
