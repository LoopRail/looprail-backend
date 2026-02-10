from unittest.mock import MagicMock

import pytest

from src.models import Otp, User
from src.types import error, NotFoundError


import httpx


@pytest.mark.asyncio
class TestVerifyOnboardingOtp:
    async def test_verify_onboarding_otp_success(
        self,
        client: httpx.AsyncClient,
        mock_get_otp_token: MagicMock,
        mock_config: MagicMock,
        mock_jwt_usecase: MagicMock,
        mock_user_usecases: MagicMock,
        mock_otp_usecase: MagicMock,
        test_otp_onboarding: Otp,
        test_user_obj: User,
    ):
        # Mock dependencies
        mock_otp_usecase.get_otp.return_value = (test_otp_onboarding, None)
        mock_otp_usecase.update_otp.return_value = None
        mock_otp_usecase.delete_otp.return_value = None
        mock_otp_usecase.verify_code.return_value = True
        mock_user_usecases.get_user_by_email.return_value = (test_user_obj, None)
        mock_user_usecases.save.return_value = (test_user_obj, None)
        mock_jwt_usecase.create_token.return_value = "mock_access_token"

        response = client.post(
            "/api/v1/verify/onbaording-otp",
            json={"code": "123456", "otp_type": "onboarding_email_verification"},
            headers={"X-OTP-Token": mock_get_otp_token.return_value},
        )

        assert response.status_code == 200
        assert response.json()["message"] == "OTP verified successfully"
        assert response.json()["access-token"] == "mock_access_token"

        mock_otp_usecase.get_otp.assert_called_once()
        mock_otp_usecase.verify_code.assert_called_once()
        mock_user_usecases.get_user_by_email.assert_called_once_with(
            user_email=test_otp_onboarding.user_email
        )
        assert test_user_obj.is_email_verified is True
        mock_user_usecases.save.assert_called_once_with(test_user_obj)
        mock_jwt_usecase.create_token.assert_called_once()

    async def test_verify_onboarding_otp_invalid_otp_type(
        self,
        client: httpx.AsyncClient,
        mock_get_otp_token: MagicMock,
        mock_otp_usecase: MagicMock,
        test_otp_onboarding: Otp,
    ):
        # Mock OTP with a different type
        invalid_otp = test_otp_onboarding
        invalid_otp.otp_type = "invalid_type"

        mock_otp_usecase.get_otp.return_value = (invalid_otp, None)

        response = client.post(
            "/api/v1/verify/onbaording-otp",
            json={"code": "123456", "otp_type": "onboarding_email_verification"},
            headers={"X-OTP-Token": mock_get_otp_token.return_value},
        )

        assert response.status_code == 400
        assert response.json()["message"] == "Invalid otp type"
        mock_otp_usecase.get_otp.assert_called_once()

    async def test_verify_onboarding_otp_user_not_found(
        self,
        client: httpx.AsyncClient,
        mock_get_otp_token: MagicMock,
        mock_otp_usecase: MagicMock,
        mock_user_usecases: MagicMock,
        test_otp_onboarding: Otp,
    ):
        mock_otp_usecase.get_otp.return_value = (test_otp_onboarding, None)
        mock_otp_usecase.verify_code.return_value = True
        mock_user_usecases.get_user_by_email.return_value = (None, NotFoundError)

        response = client.post(
            "/api/v1/verify/onbaording-otp",
            json={"code": "123456", "otp_type": "onboarding_email_verification"},
            headers={"X-OTP-Token": mock_get_otp_token.return_value},
        )

        assert response.status_code == 404
        assert response.json()["message"] == "user not found"
        mock_otp_usecase.get_otp.assert_called_once()
        mock_otp_usecase.verify_code.assert_called_once()
        mock_user_usecases.get_user_by_email.assert_called_once_with(
            user_email=test_otp_onboarding.user_email
        )

    async def test_verify_onboarding_otp_user_save_fails(
        self,
        client: httpx.AsyncClient,
        mock_get_otp_token: MagicMock,
        mock_otp_usecase: MagicMock,
        mock_user_usecases: MagicMock,
        test_otp_onboarding: Otp,
        test_user_obj: User,
    ):
        mock_otp_usecase.get_otp.return_value = (test_otp_onboarding, None)
        mock_otp_usecase.verify_code.return_value = True
        mock_user_usecases.get_user_by_email.return_value = (test_user_obj, None)
        mock_user_usecases.save.return_value = (None, error("Database error"))

        response = client.post(
            "/api/v1/verify/onbaording-otp",
            json={"code": "123456", "otp_type": "onboarding_email_verification"},
            headers={"X-OTP-Token": mock_get_otp_token.return_value},
        )

        assert response.status_code == 404
        assert response.json()["message"] == "user not found"
        mock_otp_usecase.get_otp.assert_called_once()
        mock_otp_usecase.verify_code.assert_called_once()
        mock_user_usecases.get_user_by_email.assert_called_once_with(
            user_email=test_otp_onboarding.user_email
        )
        assert test_user_obj.is_email_verified is True
        mock_user_usecases.save.assert_called_once_with(test_user_obj)
