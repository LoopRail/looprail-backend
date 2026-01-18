from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import BearerToken
from src.main import app
from src.models import User
from src.types import AccessToken, TokenType, error


@pytest.fixture(name="authenticated_client")
def authenticated_client_fixture(
    client: TestClient,
    test_user: tuple[User, str],
    mock_user_usecases: MagicMock,
    mock_session_usecase: MagicMock,
    mock_jwt_usecase: MagicMock,
) -> tuple[TestClient, str, str]:
    user, _ = test_user
    # Mock user authentication
    mock_user_usecases.authenticate_user.return_value = (user, None)

    # Mock session creation
    session_id = f"ses_{uuid4()}"
    mock_session = MagicMock()
    mock_session.id = session_id
    mock_session.user_id = user.id
    raw_refresh_token = f"rft_{uuid4()}"
    mock_session_usecase.create_session.return_value = (mock_session, raw_refresh_token)

    mock_access_token = "mock_access_token"
    mock_jwt_usecase.create_token.return_value = mock_access_token

    return client, mock_access_token, raw_refresh_token


def test_login_success(
    client: TestClient,
    test_user: tuple[User, str],
    mock_user_usecases: MagicMock,
    mock_session_usecase: MagicMock,
    mock_jwt_usecase: MagicMock,
):
    user, password = test_user
    login_data = {"email": user.email, "password": password}
    headers = {"X-Device-ID": "test_device_id", "X-Platform": "web"}

    # Mock use case return values
    mock_user_usecases.authenticate_user.return_value = (user, None)

    session_id = f"ses_{uuid4()}"
    mock_session = MagicMock()
    mock_session.id = session_id
    mock_session.user_id = user.id
    raw_refresh_token = f"rft_{uuid4()}"
    mock_session_usecase.create_session.return_value = (
        mock_session,
        raw_refresh_token,
        None,
    )

    mock_jwt_usecase.create_token.return_value = "mock_access_token_string"

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
        platform=headers["X-Platform"],
        ip_address="testclient",
    )
    mock_jwt_usecase.create_token.assert_called_once()  # Detailed assertion can be added if needed


def test_login_invalid_credentials(
    client: TestClient, test_user: tuple[User, str], mock_user_usecases: MagicMock
):
    user, _ = test_user
    login_data = {"email": user.email, "password": "wrongpassword"}
    headers = {"X-Device-ID": "test_device_id", "X-Platform": "web"}

    # Mock user authentication to return an error
    mock_user_usecases.authenticate_user.return_value = (
        None,
        error("Invalid credentials"),
    )

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
    mock_session_usecase.get_session.return_value = (mock_session, None)

    new_raw_refresh_token_value = "mock_new_raw_refresh_token_string"
    mock_session_usecase.rotate_refresh_token.return_value = (
        new_raw_refresh_token_value,
        None,
    )

    new_access_token_value = "mock_new_access_token_string"
    mock_jwt_usecase.create_token.return_value = new_access_token_value

    response = client.post(
        "/api/v1/auth/token",
        json={"refresh-token": refresh_token},
        headers={"X-Device-ID": "test_device_id", "X-Platform": "web"},
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
        new_refresh_token_string=new_raw_refresh_token_value,
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

    response = client.post(
        "/api/v1/auth/token",
        json={"refresh-token": "invalid_token"},
        headers={"X-Device-ID": "test_device_id", "X-Platform": "web"},
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
    mock_session_usecase.get_session.return_value = (mock_session, None)

    new_raw_refresh_token_value = "mock_new_raw_refresh_token_string_for_reuse"
    mock_session_usecase.rotate_refresh_token.return_value = (
        new_raw_refresh_token_value,
        None,
    )

    new_access_token_value = "mock_new_access_token_string_for_reuse"
    mock_jwt_usecase.create_token.return_value = new_access_token_value

    # First refresh - should be successful
    response1 = client.post(
        "/api/v1/auth/token",
        json={"refresh-token": initial_refresh_token},
        headers={"X-Device-ID": "test_device_id", "X-Platform": "web"},
    )
    assert response1.status_code == 200
    assert "access-token" in response1.json()
    assert "refresh-token" in response1.json()

    # Attempt to use the old refresh token again - should trigger reuse detection
    response2 = client.post(
        "/api/v1/auth/token",
        json={"refresh-token": initial_refresh_token},
        headers={"X-Device-ID": "test_device_id", "X-Platform": "web"},
    )
    assert response2.status_code == 401
    assert response2.json() == {"error": "Refresh token reused. Please log in again."}

    # assert mock_jwt_usecase.get_valid_refresh_token_by_hash.call_count == 2
    assert mock_session_usecase.revoke_session.call_count == 1
    mock_session_usecase.revoke_session.assert_called_once_with(
        mock_refresh_token_db_first_call.session_id
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

    mock_session_usecase.revoke_session.assert_called_once_with(mock_session_id)

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
        user.get_prefixed_id()
    )

    # Clear the override
    app.dependency_overrides.clear()
