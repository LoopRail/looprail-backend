import os

os.environ["TESTING"] = "true"

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from src.main import app
from src.types import Error

client = TestClient(app)


@patch("src.api.versions.v1.handlers.auth_router.get_otp_usecase")
@patch("src.api.versions.v1.handlers.auth_router.get_resend_service")
def test_send_otp_success(mock_get_resend_service, mock_get_otp_usecase):
    # Arrange
    mock_otp_usecase = MagicMock()
    mock_otp_usecase.generate_otp = AsyncMock(
        return_value=("123456", "test_token", None)
    )
    mock_get_otp_usecase.return_value = mock_otp_usecase

    mock_resend_service = MagicMock()
    mock_resend_service.send_otp = AsyncMock(return_value=(None, None))
    mock_get_resend_service.return_value = mock_resend_service

    # Act
    response = client.post("/api/v1/auth/send-otp", json={"email": "test@example.com"})

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": "OTP sent successfully."}
    assert "X-OTP-Token" in response.headers
    assert response.headers["X-OTP-Token"] == "test_token"
    mock_otp_usecase.generate_otp.assert_called_once_with(user_email="test@example.com")
    mock_resend_service.send_otp.assert_called_once_with(
        to="test@example.com",
        _from="team@looprail.com",
        otp_code="123456",
    )


@patch("src.api.versions.v1.handlers.auth_router.get_otp_usecase")
def test_send_otp_generate_otp_fails(mock_get_otp_usecase):
    # Arrange
    mock_otp_usecase = MagicMock()
    mock_otp_usecase.generate_otp = AsyncMock(
        return_value=("", "", Error("Failed to generate OTP"))
    )
    mock_get_otp_usecase.return_value = mock_otp_usecase

    # Act
    response = client.post("/api/v1/auth/send-otp", json={"email": "test@example.com"})

    # Assert
    assert response.status_code == 400
    assert response.json() == {"detail": "Failed to generate OTP"}


@patch("src.api.versions.v1.handlers.auth_router.get_otp_usecase")
@patch("src.api.versions.v1.handlers.auth_router.get_resend_service")
def test_send_otp_send_email_fails(mock_get_resend_service, mock_get_otp_usecase):
    # Arrange
    mock_otp_usecase = MagicMock()
    mock_otp_usecase.generate_otp = AsyncMock(
        return_value=("123456", "test_token", None)
    )
    mock_get_otp_usecase.return_value = mock_otp_usecase

    mock_resend_service = MagicMock()
    mock_resend_service.send_otp = AsyncMock(
        return_value=(None, Error("Failed to send email"))
    )
    mock_get_resend_service.return_value = mock_resend_service

    # Act
    response = client.post("/api/v1/auth/send-otp", json={"email": "test@example.com"})

    # Assert
    assert response.status_code == 500
    assert response.json() == {"detail": "Failed to send OTP."}
