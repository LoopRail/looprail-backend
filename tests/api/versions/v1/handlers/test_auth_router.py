import time
from unittest.mock import AsyncMock, MagicMock, patch

from src.api.dependencies import verify_otp_dep
from src.main import app
from src.models.otp_model import Otp
from tests.conftest import client


def test_verify_otp_expired_email_otp():
    # Arrange
    mock_otp_usecase = MagicMock()
    otp = Otp(
        code_hash="hashed_code",
        user_email="andrew@looprail.xyz",
        expires_at=int(time.time() - 2),
    )
    mock_otp_usecase.get_otp = AsyncMock(return_value=(otp, None))
    mock_otp_usecase.delete_otp = AsyncMock(return_value=None)

    app.dependency_overrides[verify_otp_dep] = lambda: mock_otp_usecase

    # Act
    response = client.post(
        "/api/v1/verify/onbaording-otp",
        json={"code": "123456", "otp-type": "onboarding_email_verification"},
        headers={"X-OTP-Token": "test_token"},
    )

    # Assert
    assert response.status_code == 400

    app.dependency_overrides.clear()


def test_verify_otp_max_attempts_exceeded_email_otp():
    # Arrange
    mock_otp_usecase = MagicMock()
    otp = Otp(
        code_hash="hashed_code",
        user_email="andrew@looprail.xyz",
        attempts=3,
    )
    mock_otp_usecase.get_otp = AsyncMock(return_value=(otp, None))
    mock_otp_usecase.delete_otp = AsyncMock(return_value=None)

    app.dependency_overrides[verify_otp_dep] = lambda: mock_otp_usecase

    # Act
    response = client.post(
        "/api/v1/verify/onbaording-otp",
        json={"code": "123456", "otp-type": "onboarding_email_verification"},
        headers={"X-OTP-Token": "test_token"},
    )

    # Assert
    assert response.status_code == 400

    app.dependency_overrides.clear()


def test_verify_otp_invalid_code():
    # Arrange
    mock_otp_usecase = MagicMock()
    otp = Otp(
        code_hash="hashed_code",
        user_email="andrew@looprail.xyz",
    )
    mock_otp_usecase.get_otp = AsyncMock(return_value=(otp, None))
    mock_otp_usecase.update_otp = AsyncMock(return_value=None)
    mock_otp_usecase.verify_code = AsyncMock(return_value=False)

    app.dependency_overrides[verify_otp_dep] = lambda: mock_otp_usecase

    # Act
    response = client.post(
        "/api/v1/verify/onbaording-otp",
        json={"code": "wrong_code", "otp-type": "onboarding_email_verification"},
        headers={"X-OTP-Token": "test_token"},
    )

    # Assert
    assert response.status_code == 400

    app.dependency_overrides.clear()

@patch("src.api.versions.v1.handlers.auth_router.get_user_usecases")
@patch("src.api.versions.v1.handlers.auth_router.httpx")
def test_create_user_invalid_country_code(mock_httpx, mock_get_user_usecases):
    # Arrange
    # Mock user_usecases to prevent actual database interaction if validation passes unexpectedly
    mock_user_usecases = MagicMock()
    mock_user_usecases.create_user = AsyncMock()
    mock_get_user_usecases.return_value = mock_user_usecases

    # Mock httpx to prevent actual HTTP calls in the background task
    mock_httpx.AsyncClient.return_value.__aenter__.return_value.post = AsyncMock()

    user_data = {
        "email": "test@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "country_code": "XYZ",  # Invalid country code
        "gender": "male",
        "phone_number": {
            "code": "+1",
            "number": "1234567890",
            "country_code": "US",
        },
        "password": "password123",
        "username": "john.doe",
    }

    # Act
    response = client.post("/api/v1/auth/create-user", json=user_data)

    # Assert
    assert response.status_code == 400
    mock_user_usecases.create_user.assert_not_called()
    mock_httpx.AsyncClient.return_value.__aenter__.return_value.post.assert_not_called()


@patch("src.api.versions.v1.handlers.auth_router.get_user_usecases")
@patch("src.api.versions.v1.handlers.auth_router.httpx")
def test_create_user_invalid_phone_number_format(mock_httpx, mock_get_user_usecases):
    # Arrange
    mock_user_usecases = MagicMock()
    mock_user_usecases.create_user = AsyncMock()
    mock_get_user_usecases.return_value = mock_user_usecases

    mock_httpx.AsyncClient.return_value.__aenter__.return_value.post = AsyncMock()

    user_data = {
        "email": "test@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "country_code": "US",
        "gender": "male",
        "phone_number": {
            "code": "+434",
            "number": "90000000000",
            "country_code": "US",
        },
        "password": "password123",
        "username": "john.doe",
    }

    # Act
    response = client.post("/api/v1/auth/create-user", json=user_data)

    # Assert
    assert response.status_code == 400
    mock_user_usecases.create_user.assert_not_called()
    mock_httpx.AsyncClient.return_value.__aenter__.return_value.post.assert_not_called()


@patch("src.api.versions.v1.handlers.auth_router.get_user_usecases")
@patch("src.api.versions.v1.handlers.auth_router.httpx")
def test_create_user_invalid_email(mock_httpx, mock_get_user_usecases):
    # Arrange
    mock_user_usecases = MagicMock()
    mock_user_usecases.create_user = AsyncMock()
    mock_get_user_usecases.return_value = mock_user_usecases

    mock_httpx.AsyncClient.return_value.__aenter__.return_value.post = AsyncMock()

    user_data = {
        "email": "admin@example.com",  # Invalid email
        "first_name": "John",
        "last_name": "Doe",
        "country_code": "US",
        "gender": "male",
        "phone_number": {
            "code": "+1",
            "number": "1234567890",
            "country_code": "US",
        },
        "password": "password123",
        "username": "john.doe",
    }

    # Act
    response = client.post("/api/v1/auth/create-user", json=user_data)

    # Assert
    assert response.status_code == 400
    mock_user_usecases.create_user.assert_not_called()
    mock_httpx.AsyncClient.return_value.__aenter__.return_value.post.assert_not_called()


@patch("src.api.versions.v1.handlers.auth_router.get_user_usecases")
@patch("src.api.versions.v1.handlers.auth_router.httpx")
def test_create_user_disposable_email(mock_httpx, mock_get_user_usecases):
    # Arrange
    mock_user_usecases = MagicMock()
    mock_user_usecases.create_user = AsyncMock()
    mock_get_user_usecases.return_value = mock_user_usecases

    mock_httpx.AsyncClient.return_value.__aenter__.return_value.post = AsyncMock()

    user_data = {
        "email": "test@mailinator.com",  # Disposable email
        "first_name": "John",
        "last_name": "Doe",
        "country_code": "US",
        "gender": "male",
        "phone_number": {
            "code": "+1",
            "number": "1234567890",
            "country_code": "US",
        },
        "password": "password123",
        "username": "john.doe",
    }

    # Act
    response = client.post("/api/v1/auth/create-user", json=user_data)

    # Assert
    assert response.status_code == 400
    mock_user_usecases.create_user.assert_not_called()
    mock_httpx.AsyncClient.return_value.__aenter__.return_value.post.assert_not_called()


@patch("src.api.versions.v1.handlers.auth_router.get_user_usecases")
@patch("src.api.versions.v1.handlers.auth_router.httpx")
def test_create_user_invalid_gender(mock_httpx, mock_get_user_usecases):
    # Arrange
    mock_user_usecases = MagicMock()
    mock_user_usecases.create_user = AsyncMock()
    mock_get_user_usecases.return_value = mock_user_usecases

    mock_httpx.AsyncClient.return_value.__aenter__.return_value.post = AsyncMock()

    user_data = {
        "email": "test@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "country_code": "US",
        "gender": "other",  # Invalid gender
        "phone_number": {
            "code": "+1",
            "number": "1234567890",
            "country_code": "US",
        },
        "password": "password123",
        "username": "john.doe",
    }

    # Act
    response = client.post("/api/v1/auth/create-user", json=user_data)

    # Assert
    assert response.status_code == 400
    mock_user_usecases.create_user.assert_not_called()
    mock_httpx.AsyncClient.return_value.__aenter__.return_value.post.assert_not_called()
