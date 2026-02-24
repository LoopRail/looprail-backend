from unittest.mock import ANY, MagicMock, AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.models import User
from src.dtos import UserPublic
from src.types import AccessToken, TokenType, error, Platform
from src.api.dependencies import get_auth_lock_service, get_geolocation_service, get_notification_usecase, get_resend_service
from src.api.versions.v1.handlers.auth_router import login_auth_lock


@pytest.fixture(name="authenticated_client")
def authenticated_client_fixture(
    client: TestClient,
    test_user: tuple[User, str],
    mock_user_usecases: MagicMock,
    mock_session_usecase: MagicMock,
    mock_jwt_usecase: MagicMock,
) -> tuple[TestClient, str, str]:
    user, password = test_user

    # Mock user authentication
    mock_user_usecases.authenticate_user.return_value = (user, None)
    user_public_data = UserPublic.model_validate(user).model_dump(exclude_none=True)
    mock_user_usecases.load_public_user.return_value = (user_public_data, None)

    # Mock session creation
    session_id = f"ses_{uuid4()}"
    mock_session = MagicMock()
    mock_session.id = session_id.replace("ses_", "")
    mock_session.user_id = user.id
    mock_session.get_prefixed_id.return_value = session_id
    raw_refresh_token = f"rft_{uuid4()}"
    mock_session_usecase.create_session.return_value = (mock_session, raw_refresh_token, None)

    mock_access_token = "mock_access_token"
    mock_jwt_usecase.create_token.return_value = mock_access_token

    mock_auth_lock = AsyncMock()
    mock_auth_lock.is_account_locked.return_value = (False, None)
    mock_auth_lock.increment_failed_attempts.return_value = (1, None)
    mock_auth_lock.reset_failed_attempts.return_value = None
    app.dependency_overrides[login_auth_lock] = lambda: mock_auth_lock

    mock_geo = AsyncMock()
    mock_geo.get_location.return_value = (None, None)
    app.dependency_overrides[get_geolocation_service] = lambda: mock_geo

    mock_notif = MagicMock()
    app.dependency_overrides[get_notification_usecase] = lambda: mock_notif

    mock_resend = MagicMock()
    app.dependency_overrides[get_resend_service] = lambda: mock_resend

    # Perform actual login so the refresh token is real
    device_id = f"device_{uuid4()}"
    response = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": password, "allow_notifications": False},
        headers={"X-Device-ID": device_id, "X-Platform": "web"},
    )
    assert response.status_code == 200, f"Login failed in fixture: {response.json()}"
    issued_refresh_token = response.json()["refresh-token"]

    return client, mock_access_token, issued_refresh_token


def test_login_success(
    client: TestClient,
    test_user: tuple[User, str],
    mock_user_usecases: MagicMock,
    mock_session_usecase: MagicMock,
    mock_jwt_usecase: MagicMock,
):
    user, password = test_user
    device_id = f"device_{uuid4()}"
    login_data = {"email": user.email, "password": password}
    headers = {"X-Device-ID": device_id, "X-Platform": "web"}

    mock_user_usecases.authenticate_user.return_value = (user, None)
    user_public_data = UserPublic.model_validate(user).model_dump(exclude_none=True)
    mock_user_usecases.load_public_user.return_value = (user_public_data, None)

    session_id = f"ses_{uuid4()}"
    mock_session = MagicMock()
    mock_session.id = session_id.replace("ses_", "")
    mock_session.user_id = user.id
    mock_session.get_prefixed_id.return_value = session_id
    raw_refresh_token = f"rft_{uuid4()}"
    mock_session_usecase.create_session.return_value = (
        mock_session,
        raw_refresh_token,
        None,
    )

    mock_jwt_usecase.create_token.return_value = "mock_access_token_string"

    # Mock other dependencies to avoid unawaited coroutine errors
    mock_auth_lock = AsyncMock()
    mock_auth_lock.is_account_locked.return_value = (False, None)
    mock_auth_lock.increment_failed_attempts.return_value = (1, None)
    mock_auth_lock.reset_failed_attempts.return_value = None
    app.dependency_overrides[login_auth_lock] = lambda: mock_auth_lock

    mock_geo = AsyncMock()
    geo_data = MagicMock()
    geo_data.status = "success"
    geo_data.city = "Test City"
    geo_data.regionName = "Test Region"
    geo_data.country = "Test Country"
    mock_geo.get_location.return_value = (geo_data, None)
    app.dependency_overrides[get_geolocation_service] = lambda: mock_geo
    
    mock_notif = MagicMock()
    app.dependency_overrides[get_notification_usecase] = lambda: mock_notif

    mock_resend = MagicMock()
    app.dependency_overrides[get_resend_service] = lambda: mock_resend

    response = client.post("/api/v1/auth/login", json=login_data, headers=headers)

    assert response.status_code == 200
    response_json = response.json()
    assert "access-token" in response_json
    assert "refresh-token" in response_json
    assert "user" in response_json
    assert response_json["user"]["email"] == user.email
    assert response_json["access-token"] == "mock_access_token_string"
    assert response_json["refresh-token"] == raw_refresh_token

    # Assert that use cases were called correctly
    mock_user_usecases.authenticate_user.assert_called_once_with(
        email=login_data["email"], password=login_data["password"]
    )
    mock_session_usecase.create_session.assert_called_once_with(
        user_id=user.id,
        device_id=headers["X-Device-ID"],
        platform=Platform.WEB,
        ip_address="testclient",
        allow_notifications=False,
        fcm_token=None,
    )
    mock_jwt_usecase.create_token.assert_called_once()  # Detailed assertion can be added if needed


def test_login_invalid_credentials(
    client: TestClient, test_user: tuple[User, str], mock_user_usecases: MagicMock
):
    user, _ = test_user
    device_id = f"device_{uuid4()}"
    login_data = {"email": user.email, "password": "wrongpassword"}
    headers = {"X-Device-ID": device_id, "X-Platform": "web"}

    # Mock user authentication to return an error
    mock_user_usecases.authenticate_user.return_value = (
        None,
        error("Invalid credentials"),
    )

    # Mock other dependencies to avoid unawaited coroutine errors
    mock_auth_lock = AsyncMock()
    mock_auth_lock.is_account_locked.return_value = (False, None)
    mock_auth_lock.increment_failed_attempts.return_value = (1, None)
    mock_auth_lock.reset_failed_attempts.return_value = None
    app.dependency_overrides[login_auth_lock] = lambda: mock_auth_lock

    mock_resend = MagicMock()
    app.dependency_overrides[get_resend_service] = lambda: mock_resend

    response = client.post("/api/v1/auth/login", json=login_data, headers=headers)

    assert response.status_code == 401
    assert response.json() == {"message": "Invalid credentials"}
    mock_user_usecases.authenticate_user.assert_called_once_with(
        email=login_data["email"], password=login_data["password"]
    )


def test_refresh_token_success(
    client: TestClient,
    authenticated_client: tuple[TestClient, str, str],
    mock_session_usecase: MagicMock,
    mock_jwt_usecase: MagicMock,
):
    _, access_token, refresh_token = authenticated_client

    mock_refresh_token_db = MagicMock()
    mock_refresh_token_db.id = uuid4()
    mock_refresh_token_db.session_id = f"ses_{uuid4()}"
    mock_refresh_token_db.replaced_by_hash = None
    mock_session_usecase.get_valid_refresh_token_by_hash.return_value = (
        mock_refresh_token_db,
        None,
    )

    mock_session = MagicMock()
    mock_session.id = mock_refresh_token_db.session_id
    mock_session.user_id = f"usr_{uuid4()}"
    mock_session.get_prefixed_id.return_value = str(mock_session.id)
    mock_session_usecase.get_session.return_value = (mock_session, None)

    new_raw_refresh_token_value = "mock_new_raw_refresh_token_string"
    mock_session_usecase.rotate_refresh_token.return_value = (
        new_raw_refresh_token_value,
        None,
    )

    new_access_token_value = "mock_new_access_token_string"
    mock_jwt_usecase.create_token.return_value = new_access_token_value

    device_id = f"device_{uuid4()}"
    response = client.post(
        "/api/v1/auth/token",
        json={"refresh_token": refresh_token},
        headers={"X-Device-ID": device_id, "X-Platform": "web"},
    )

    assert response.status_code == 200
    response_json = response.json()
    assert "access-token" in response_json
    assert "refresh-token" in response_json
    assert response_json["access-token"] == new_access_token_value
    assert response_json["refresh-token"] == new_raw_refresh_token_value

    mock_session_usecase.get_valid_refresh_token_by_hash.assert_called_once()
    mock_session_usecase.get_session.assert_called_once_with(
        mock_refresh_token_db.session_id
    )
    mock_session_usecase.rotate_refresh_token.assert_called_once_with(
        old_refresh_token=mock_refresh_token_db,
        new_refresh_token_string=ANY,
    )
    assert mock_jwt_usecase.create_token.call_count == 1


def test_refresh_token_invalid_token(
    client: TestClient, mock_session_usecase: MagicMock
):
    # Mock SessionUseCase.get_valid_refresh_token_by_hash to return an error
    mock_session_usecase.get_valid_refresh_token_by_hash.return_value = (
        None,
        error("Invalid or expired refresh token"),
    )

    device_id = f"device_{uuid4()}"
    response = client.post(
        "/api/v1/auth/token",
        json={"refresh_token": f"rft_{uuid4()}"},
        headers={"X-Device-ID": device_id, "X-Platform": "web"},
    )
    assert response.status_code == 401
    assert response.json() == {"message": "Invalid or expired refresh token"}
    mock_session_usecase.get_valid_refresh_token_by_hash.assert_called_once()


def test_refresh_token_reuse_detection(
    client: TestClient,
    authenticated_client: tuple[TestClient, str, str],
    mock_session_usecase: MagicMock,
    mock_jwt_usecase: MagicMock,
):
    _, initial_access_token, initial_refresh_token = authenticated_client

    mock_refresh_token_db_first_call = MagicMock()
    mock_refresh_token_db_first_call.id = uuid4()
    mock_refresh_token_db_first_call.session_id = f"ses_{uuid4()}"
    mock_refresh_token_db_first_call.replaced_by_hash = None

    mock_refresh_token_db_second_call = MagicMock()
    mock_refresh_token_db_second_call.id = mock_refresh_token_db_first_call.id
    mock_refresh_token_db_second_call.session_id = (
        mock_refresh_token_db_first_call.session_id
    )
    mock_refresh_token_db_second_call.replaced_by_hash = (
        "some_hash_value"  # Indicate reuse
    )

    mock_session_usecase.get_valid_refresh_token_by_hash.side_effect = [
        (mock_refresh_token_db_first_call, None),
        (mock_refresh_token_db_second_call, None),
    ]

    mock_session = MagicMock()
    mock_session.id = mock_refresh_token_db_first_call.session_id
    mock_session.user_id = f"usr_{uuid4()}"
    mock_session.get_prefixed_id.return_value = str(mock_session.id)
    mock_session_usecase.get_session.return_value = (mock_session, None)

    new_raw_refresh_token_value = "mock_new_raw_refresh_token_string_for_reuse"
    mock_session_usecase.rotate_refresh_token.return_value = (
        new_raw_refresh_token_value,
        None,
    )

    new_access_token_value = "mock_new_access_token_string_for_reuse"
    mock_jwt_usecase.create_token.return_value = new_access_token_value

    device_id = f"device_{uuid4()}"
    # First refresh - should be successful
    response1 = client.post(
        "/api/v1/auth/token",
        json={"refresh_token": initial_refresh_token},
        headers={"X-Device-ID": device_id, "X-Platform": "web"},
    )
    assert response1.status_code == 200
    assert "access-token" in response1.json()
    assert "refresh-token" in response1.json()

    # Attempt to use the old refresh token again - should trigger reuse detection
    response2 = client.post(
        "/api/v1/auth/token",
        json={"refresh_token": initial_refresh_token},
        headers={"X-Device-ID": device_id, "X-Platform": "web"},
    )
    assert response2.status_code == 401
    assert response2.json() == {"error": "Refresh token reused. Please log in again."}

    # assert mock_jwt_usecase.get_valid_refresh_token_by_hash.call_count == 2
    assert mock_session_usecase.revoke_session.call_count == 1
    mock_session_usecase.revoke_session.assert_called_once_with(
        mock_refresh_token_db_first_call.session_id.replace("ses_", "")
    )
    assert mock_jwt_usecase.create_token.call_count == 1


def test_logout_success(
    client: TestClient,
    authenticated_client: tuple[TestClient, str, str],
    mock_session_usecase: MagicMock,
    mock_jwt_usecase: MagicMock,
):
    _, access_token, _ = authenticated_client
    mock_session_id = f"ses_{uuid4()}"
    mock_user_id = str(uuid4())
    mock_platform = "web"
    mock_access_token_obj = AccessToken(
        sub=f"access_ses_{mock_session_id}",
        user_id=f"usr_{mock_user_id}",
        token_type=TokenType.ACCESS_TOKEN,
        session_id=mock_session_id,
        platform="android",
    )

    # Mock jwt_usecase.verify_token to return our mock AccessToken
    mock_jwt_usecase.verify_token.return_value = (mock_access_token_obj, None)

    # Mock SessionUseCase.revoke_session
    mock_session_usecase.revoke_session.return_value = None

    response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.json() == {"message": "Logged out successfully"}

    mock_session_usecase.revoke_session.assert_called_once_with(mock_session_id.split("_")[-1])

    # Clear the override
    app.dependency_overrides.clear()


def test_logout_all_success(
    client: TestClient,
    test_user: tuple[User, str],
    mock_session_usecase: MagicMock,
    mock_jwt_usecase: MagicMock,
):
    user, _ = test_user
    mock_session_id = f"ses_{uuid4()}"
    mock_platform = "web"
    mock_access_token_obj = AccessToken(
        sub=f"access_ses_{mock_session_id}",
        user_id=user.get_prefixed_id(),
        token_type=TokenType.ACCESS_TOKEN,
        session_id=mock_session_id,
        platform="android",
    )

    # Mock jwt_usecase.verify_token to return our mock AccessToken
    mock_jwt_usecase.verify_token.return_value = (mock_access_token_obj, None)
    # Mock SessionUseCase.revoke_all_user_sessions
    mock_session_usecase.revoke_all_user_sessions.return_value = None

    response = client.post(
        "/api/v1/auth/logout-all",
        headers={"Authorization": "Bearer mock_access_token_for_logout_all"},
    )

    assert response.status_code == 200
    assert response.json() == {"message": "Logged out from all sessions successfully"}

    mock_session_usecase.revoke_all_user_sessions.assert_called_once_with(
        str(user.id)
    )

    # Clear the override
    app.dependency_overrides.clear()


def test_login_with_fcm_token_success(
    client: TestClient,
    test_user: tuple[User, str],
    mock_user_usecases: MagicMock,
    mock_session_usecase: MagicMock,
    mock_jwt_usecase: MagicMock,
):
    user, password = test_user
    fcm_token = "test_fcm_token"
    device_id = f"device_{uuid4()}"
    login_data = {"email": user.email, "password": password, "fcm_token": fcm_token}
    headers = {"X-Device-ID": device_id, "X-Platform": "android"}

    mock_user_usecases.authenticate_user.return_value = (user, None)
    user_public_data = UserPublic.model_validate(user).model_dump(exclude_none=True)
    mock_user_usecases.load_public_user.return_value = (user_public_data, None)

    session_id = f"ses_{uuid4()}"
    mock_session = MagicMock()
    mock_session.id = session_id.replace("ses_", "")
    mock_session.user_id = user.id
    mock_session.get_prefixed_id.return_value = session_id
    raw_refresh_token = f"rft_{uuid4()}"
    mock_session_usecase.create_session.return_value = (
        mock_session,
        raw_refresh_token,
        None,
    )

    mock_jwt_usecase.create_token.return_value = "mock_access_token_string"

    # Mock other dependencies to avoid unawaited coroutine errors
    mock_auth_lock = AsyncMock()
    mock_auth_lock.is_account_locked.return_value = (False, None)
    mock_auth_lock.increment_failed_attempts.return_value = (1, None)
    mock_auth_lock.reset_failed_attempts.return_value = None
    app.dependency_overrides[login_auth_lock] = lambda: mock_auth_lock

    mock_geo = AsyncMock()
    geo_data = MagicMock()
    geo_data.status = "success"
    geo_data.city = "Test City"
    geo_data.regionName = "Test Region"
    geo_data.country = "Test Country"
    mock_geo.get_location.return_value = (geo_data, None)
    app.dependency_overrides[get_geolocation_service] = lambda: mock_geo
    
    mock_notif = MagicMock()
    app.dependency_overrides[get_notification_usecase] = lambda: mock_notif

    mock_resend = MagicMock()
    app.dependency_overrides[get_resend_service] = lambda: mock_resend

    response = client.post("/api/v1/auth/login", json=login_data, headers=headers)

    assert response.status_code == 200
    
    # Assert that fcm_token was passed to create_session
    mock_session_usecase.create_session.assert_called_once_with(
        user_id=user.id,
        device_id=headers["X-Device-ID"],
        platform=Platform.ANDROID,
        ip_address="testclient",
        allow_notifications=True,
        fcm_token=fcm_token,
    )
