import hashlib
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from src.models import RefreshToken
from src.models import Session as DBSession
from src.models import User
from src.utils import auth_utils
from src.types import auth_types


@pytest.fixture(name="test_user")
def test_user_fixture(db_session: Session):
    password = "testpassword"
    hashed_password_obj = auth_utils.hash_password_argon2(password)
    user = User(
        email="test@example.com",
        password_hash=hashed_password_obj.password_hash,
        salt=hashed_password_obj.salt,
        first_name="Test",
        last_name="User",
        is_email_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user, password


@pytest.fixture(name="authenticated_client")
def authenticated_client_fixture(client: TestClient, test_user: tuple[User, str]):
    user, password = test_user
    login_data = {"email": user.email, "password": password}
    headers = {"X-Device-ID": "test_device_id", "X-Platform": "web"}
    response = client.post("/api/v1/auth/login", json=login_data, headers=headers)
    assert response.status_code == 200
    tokens = response.json()
    return client, tokens["access_token"], tokens["refresh_token"]


def test_login_success(
    client: TestClient, db_session: Session, test_user: tuple[User, str]
):
    user, password = test_user
    login_data = {"email": user.email, "password": password}
    headers = {"X-Device-ID": "test_device_id", "X-Platform": "web"}

    response = client.post("/api/v1/auth/login", json=login_data, headers=headers)

    assert response.status_code == 200
    response_json = response.json()
    assert "access_token" in response_json
    assert "refresh_token" in response_json
    assert "user" in response_json
    assert response_json["user"]["email"] == user.email

    # Verify session and refresh token in DB
    session = db_session.exec(
        select(DBSession).where(DBSession.user_id == user.id)
    ).first()
    assert session is not None
    assert session.device_id == headers["X-Device-ID"]
    assert session.platform == headers["X-Platform"]
    assert session.ip_address is not None
    assert session.revoked_at is None

    refresh_token = db_session.exec(
        select(RefreshToken).where(RefreshToken.session_id == session.id)
    ).first()
    assert refresh_token is not None
    assert refresh_token.revoked_at is None
    assert refresh_token.replaced_by_hash is None
    assert refresh_token.expires_at > datetime.utcnow()


def test_login_invalid_credentials(client: TestClient, test_user: tuple[User, str]):
    user, _ = test_user
    login_data = {"email": user.email, "password": "wrongpassword"}
    headers = {"X-Device-ID": "test_device_id", "X-Platform": "web"}

    response = client.post("/api/v1/auth/login", json=login_data, headers=headers)

    assert response.status_code == 401
    assert response.json() == {"error": "Invalid credentials"}


def test_refresh_token_success(
    client: TestClient,
    db_session: Session,
    authenticated_client: tuple[TestClient, str, str],
):
    _, access_token, refresh_token = authenticated_client
    initial_refresh_token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

    response = client.post(
        "/api/v1/auth/token",
        json={"refresh_token": refresh_token},
        headers={"X-Device-ID": "test_device_id", "X-Platform": "web"},
    )

    assert response.status_code == 200
    response_json = response.json()
    assert "access_token" in response_json
    assert "refresh_token" in response_json
    assert response_json["access_token"] != access_token
    assert response_json["refresh_token"] != refresh_token

    # Verify old refresh token is replaced
    old_refresh_token_db = db_session.exec(
        select(RefreshToken).where(
            RefreshToken.token_hash == initial_refresh_token_hash
        )
    ).first()
    assert old_refresh_token_db is not None
    assert old_refresh_token_db.replaced_by_hash is not None

    # Verify new refresh token exists
    new_refresh_token_hash = hashlib.sha256(
        response_json["refresh_token"].encode()
    ).hexdigest()
    new_refresh_token_db = db_session.exec(
        select(RefreshToken).where(RefreshToken.token_hash == new_refresh_token_hash)
    ).first()
    assert new_refresh_token_db is not None
    assert new_refresh_token_db.revoked_at is None
    assert new_refresh_token_db.replaced_by_hash is None
    assert new_refresh_token_db.session_id == old_refresh_token_db.session_id


def test_refresh_token_invalid_token(client: TestClient):
    response = client.post(
        "/api/v1/auth/token",
        json={"refresh_token": "invalid_token"},
        headers={"X-Device-ID": "test_device_id", "X-Platform": "web"},
    )
    assert response.status_code == 401
    assert response.json() == {"error": "Invalid or expired refresh token"}


def test_refresh_token_reuse_detection(
    client: TestClient,
    db_session: Session,
    authenticated_client: tuple[TestClient, str, str],
):
    _, initial_access_token, initial_refresh_token = authenticated_client

    # First refresh - should be successful
    response1 = client.post(
        "/api/v1/auth/token",
        json={"refresh_token": initial_refresh_token},
        headers={"X-Device-ID": "test_device_id", "X-Platform": "web"},
    )
    assert response1.status_code == 200

    # Attempt to use the old refresh token again - should trigger reuse detection
    response2 = client.post(
        "/api/v1/auth/token",
        json={"refresh_token": initial_refresh_token},
        headers={"X-Device-ID": "test_device_id", "X-Platform": "web"},
    )
    assert response2.status_code == 401
    assert response2.json() == {"error": "Refresh token reused. Please log in again."}

    # Verify the session is revoked
    initial_refresh_token_hash = hashlib.sha256(
        initial_refresh_token.encode()
    ).hexdigest()
    old_refresh_token_db = db_session.exec(
        select(RefreshToken).where(
            RefreshToken.token_hash == initial_refresh_token_hash
        )
    ).first()
    assert old_refresh_token_db is not None
    session = db_session.exec(
        select(DBSession).where(DBSession.id == old_refresh_token_db.session_id)
    ).first()
    assert session is not None
    assert session.revoked_at is not None


def test_logout_success(
    client: TestClient,
    db_session: Session,
    authenticated_client: tuple[TestClient, str, str],
):
    _, access_token, _ = authenticated_client

    # Verify session is active initially
    initial_session = db_session.exec(
        select(DBSession).where(DBSession.revoked_at.is_(None))
    ).first()
    assert initial_session is not None

    response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.json() == {"message": "Logged out successfully"}

    # Verify session is revoked
    revoked_session = db_session.exec(
        select(DBSession).where(DBSession.id == initial_session.id)
    ).first()
    assert revoked_session is not None
    assert revoked_session.revoked_at is not None

    # Verify refresh tokens for the session are revoked
    revoked_refresh_tokens = db_session.exec(
        select(RefreshToken).where(RefreshToken.session_id == initial_session.id)
    ).all()
    for rt in revoked_refresh_tokens:
        assert rt.revoked_at is not None


def test_logout_all_success(
    client: TestClient, db_session: Session, test_user: tuple[User, str]
):
    user, password = test_user

    # Create multiple sessions for the user
    login_data = {"email": user.email, "password": password}
    headers1 = {"X-Device-ID": "device1", "X-Platform": "web"}
    response1 = client.post("/api/v1/auth/login", json=login_data, headers=headers1)
    assert response1.status_code == 200
    tokens1 = response1.json()
    access_token1 = tokens1["access_token"]

    headers2 = {"X-Device-ID": "device2", "X-Platform": "mobile"}
    response2 = client.post("/api/v1/auth/login", json=login_data, headers=headers2)
    assert response2.status_code == 200

    # Verify multiple sessions are active initially
    active_sessions_before = db_session.exec(
        select(DBSession).where(
            DBSession.user_id == user.id, DBSession.revoked_at.is_(None)
        )
    ).all()
    assert len(active_sessions_before) == 2

    response = client.post(
        "/api/v1/auth/logout-all",
        headers={"Authorization": f"Bearer {access_token1}"},
    )

    assert response.status_code == 200
    assert response.json() == {"message": "Logged out from all sessions successfully"}

    # Verify all sessions are revoked
    active_sessions_after = db_session.exec(
        select(DBSession).where(
            DBSession.user_id == user.id, DBSession.revoked_at.is_(None)
        )
    ).all()
    assert len(active_sessions_after) == 0

    all_sessions = db_session.exec(
        select(DBSession).where(DBSession.user_id == user.id)
    ).all()
    for session in all_sessions:
        assert session.revoked_at is not None
        # Verify refresh tokens for each session are revoked
        refresh_tokens = db_session.exec(
            select(RefreshToken).where(RefreshToken.session_id == session.id)
        ).all()
        for rt in refresh_tokens:
            assert rt.revoked_at is not None
