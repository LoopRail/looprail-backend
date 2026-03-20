import pytest
from unittest.mock import MagicMock, AsyncMock
import httpx
from src.types.types import OtpType, OtpStatus
from src.models.otp_model import Otp
from src.models.user_model import User

@pytest.mark.asyncio
async def test_request_password_reset_success(
    client: httpx.AsyncClient,
    mock_otp_usecase: MagicMock,
    mock_user_usecases: MagicMock,
    test_user_obj: User,
):
    # Arrange
    mock_user_usecases.get_user_by_email.return_value = (test_user_obj, None)
    mock_otp_usecase.generate_otp = AsyncMock(return_value=("123456", "test_token", None))
    
    # Act
    response = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": test_user_obj.email}
    )
    
    # Assert
    assert response.status_code == 200
    json_data = response.json()
    assert "otp-token" in json_data, f"Response JSON missing otp-token: {json_data}"
    assert json_data["otp-token"] == "test_token"
    mock_otp_usecase.generate_otp.assert_called_once_with(
        user_email=test_user_obj.email, otp_type=OtpType.PASSWORD_RESET
    )

@pytest.mark.asyncio
async def test_request_password_reset_user_not_found(
    client: httpx.AsyncClient,
    mock_user_usecases: MagicMock,
):
    # Arrange
    mock_user_usecases.get_user_by_email.return_value = (None, None)
    
    # Act
    response = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "nonexistent@example.com"}
    )
    
    # Assert
    assert response.status_code == 200
    assert "If your email is registered" in response.json()["message"]

@pytest.mark.asyncio
async def test_verify_password_reset_success(
    client: httpx.AsyncClient,
    mock_otp_usecase: MagicMock,
    mock_user_usecases: MagicMock,
    test_user_obj: User,
):
    # Arrange
    otp = Otp(
        user_email=test_user_obj.email,
        code_hash="hashed_code",
        otp_type=OtpType.PASSWORD_RESET
    )
    mock_otp_usecase.get_otp = AsyncMock(return_value=(otp, None))
    mock_otp_usecase.is_expired = MagicMock(return_value=False)
    mock_otp_usecase.update_otp = AsyncMock(return_value=None)
    mock_otp_usecase.verify_code = AsyncMock(return_value=True)
    mock_otp_usecase.delete_otp = AsyncMock(return_value=None)
    mock_user_usecases.reset_password = AsyncMock(return_value=(test_user_obj, None))
    
    # Act
    response = client.post(
        "/api/v1/auth/password-reset/verify",
        json={"code": "123456", "new_password": "NewPassword123!"},
        headers={"X-OTP-Token": "test_token"}
    )
    
    # Assert
    assert response.status_code == 200
    assert response.json()["message"] == "Password reset successfully"
    mock_user_usecases.reset_password.assert_called_once_with(
        email=test_user_obj.email, new_password="NewPassword123!"
    )

@pytest.mark.asyncio
async def test_verify_password_reset_invalid_otp(
    client: httpx.AsyncClient,
    mock_otp_usecase: MagicMock,
):
    # Arrange
    mock_otp_usecase.get_otp = AsyncMock(return_value=(None, Exception("Not found")))
    
    # Act
    response = client.post(
        "/api/v1/auth/password-reset/verify",
        json={"code": "123456", "new_password": "NewPassword123!"},
        headers={"X-OTP-Token": "invalid_token"}
    )
    
    # Assert
    assert response.status_code == 400
    assert "Invalid OTP token" in response.json()["message"]
