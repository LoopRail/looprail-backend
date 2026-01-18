import time
from unittest.mock import MagicMock

import httpx


from src.models.otp_model import Otp
from src.models.user_model import User


import pytest


@pytest.mark.asyncio
async def test_verify_otp_expired_email_otp(
    client: httpx.AsyncClient, mock_otp_usecase: MagicMock, mock_user_usecases: MagicMock, test_user_obj: User
):
    mock_user_usecases.get_user_by_email.return_value = (test_user_obj, None)
    mock_user_usecases.save.return_value = (test_user_obj, None)
    # Arrange
    otp = Otp(
        code_hash="hashed_code",
        user_email="andrew@looprail.xyz",
        expires_at=int(time.time() - 2),
    )
    mock_otp_usecase.get_otp.return_value = (otp, None)
    mock_otp_usecase.delete_otp.return_value = None

    # Act
    response = client.post(
        "/api/v1/verify/onbaording-otp",
        json={"code": "123456", "otp-type": "onboarding_email_verification"},
        headers={"X-OTP-Token": "test_token"},
    )

    # Assert
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_verify_otp_max_attempts_exceeded_email_otp(
    client: httpx.AsyncClient, mock_otp_usecase: MagicMock, mock_user_usecases: MagicMock, test_user_obj: User
):
    mock_user_usecases.get_user_by_email.return_value = (test_user_obj, None)
    mock_user_usecases.save.return_value = (test_user_obj, None)
    # Arrange
    otp = Otp(
        code_hash="hashed_code",
        user_email="andrew@looprail.xyz",
        attempts=3,
    )
    mock_otp_usecase.get_otp.return_value = (otp, None)
    mock_otp_usecase.delete_otp.return_value = None
    mock_otp_usecase.update_otp.return_value = None

    # Act
    response = client.post(
        "/api/v1/verify/onbaording-otp",
        json={"code": "123456", "otp-type": "onboarding_email_verification"},
        headers={"X-OTP-Token": "test_token"},
    )

    # Assert
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_verify_otp_invalid_code(
    client: httpx.AsyncClient, mock_otp_usecase: MagicMock, mock_user_usecases: MagicMock, test_user_obj: User
):
    mock_user_usecases.get_user_by_email.return_value = (test_user_obj, None)
    # Arrange
    otp = Otp(
        code_hash="hashed_code",
        user_email="andrew@looprail.xyz",
    )
    mock_otp_usecase.get_otp.return_value = (otp, None)
    mock_otp_usecase.update_otp.return_value = None
    mock_otp_usecase.verify_code.return_value = False

    # Act
    response = client.post(
        "/api/v1/verify/onbaording-otp",
        json={"code": "wrong_code", "otp-type": "onboarding_email_verification"},
        headers={"X-OTP-Token": "test_token"},
    )

    # Assert
    assert response.status_code == 400


def test_create_user_invalid_country_code(
    client: httpx.AsyncClient, mock_user_usecases: MagicMock
):
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


def test_create_user_invalid_phone_number_format(
    client: httpx.AsyncClient, mock_user_usecases: MagicMock
):
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


def test_create_user_invalid_email(
    client: httpx.AsyncClient, mock_user_usecases: MagicMock
):
    # Arrange
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


def test_create_user_disposable_email(
    client: httpx.AsyncClient, mock_user_usecases: MagicMock
):
    # Arrange
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


def test_create_user_invalid_gender(
    client: httpx.AsyncClient, mock_user_usecases: MagicMock
):
    # Arrange
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
