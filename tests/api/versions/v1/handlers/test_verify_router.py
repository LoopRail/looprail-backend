import time
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import (get_config, get_jwt_usecase, get_otp_usecase,
                                  get_user_usecases, verify_otp_dep)
from src.infrastructure.config_settings import Config
from src.infrastructure.settings import JWTConfig
from src.main import app
from src.models import Otp, User
from src.types import Error, NotFoundError, OtpType
from src.usecases import JWTUsecase, OtpUseCase, UserUseCase


# Re-use existing fixtures from test_auth_flow.py if possible
@pytest.fixture
def mock_user_usecases() -> MagicMock:
    mock = MagicMock(spec=UserUseCase)
    app.dependency_overrides[get_user_usecases] = lambda: mock
    yield mock
    app.dependency_overrides.clear()


@pytest.fixture
def mock_otp_usecase() -> MagicMock:
    mock = MagicMock(spec=OtpUseCase)
    app.dependency_overrides[get_otp_usecase] = lambda: mock
    yield mock
    app.dependency_overrides.clear()


@pytest.fixture
def mock_jwt_usecase() -> MagicMock:
    mock = MagicMock(spec=JWTUsecase)
    app.dependency_overrides[get_jwt_usecase] = lambda: mock
    yield mock
    app.dependency_overrides.clear()


@pytest.fixture
def mock_config() -> MagicMock:
    mock_jwt_settings = MagicMock(spec=JWTConfig)
    mock_jwt_settings.onboarding_token_expire_minutes = 15

    mock = MagicMock(spec=Config)
    mock.jwt = mock_jwt_settings

    app.dependency_overrides[get_config] = lambda: mock
    yield mock
    app.dependency_overrides.clear()


@pytest.fixture
def mock_verify_otp_dep() -> MagicMock:
    mock = MagicMock()
    app.dependency_overrides[verify_otp_dep] = lambda: mock
    yield mock
    app.dependency_overrides.clear()


@pytest.fixture
def test_otp_onboarding() -> Otp:
    return Otp(
        user_email="test@example.com",
        otp_type=OtpType.ONBOARDING_EMAIL_VERIFICATION,
        code_hash="hashed_code",
        is_active=True,
        attempts=0,
        expires_at=int(time.time() + 3600),  # Example future date
    )


@pytest.fixture
def test_user() -> User:
    return User(
        id=uuid4(),
        email="test@example.com",
        first_name="Test",
        last_name="User",
        is_email_verified=False,
        username="testuser",
        password_hash="hashed_password",
        salt="salt",
    )


class TestVerifyOnboardingOtp:
    @pytest.mark.asyncio
    async def test_verify_onboarding_otp_success(
        self,
        client: TestClient,
        mock_verify_otp_dep: MagicMock,
        mock_config: MagicMock,
        mock_jwt_usecase: MagicMock,
        mock_user_usecases: MagicMock,
        test_otp_onboarding: Otp,
        test_user: User,
    ):
        # Mock dependencies
        mock_verify_otp_dep.return_value = test_otp_onboarding
        mock_user_usecases.get_user_by_email.return_value = (test_user, None)
        mock_user_usecases.save.return_value = (test_user, None)
        # mock_jwt_usecase.create_access_token.return_value = "mock_access_token"

        response = client.post("/api/v1/verify/onbaording-otp")

        assert response.status_code == 200
        assert response.json()["message"] == "OTP verified successfully"
        assert response.json()["access_token"] == "mock_access_token"

        mock_verify_otp_dep.assert_called_once()
        mock_user_usecases.get_user_by_email.assert_called_once_with(
            user_email=test_otp_onboarding.user_email
        )
        assert test_user.is_email_verified is True
        mock_user_usecases.save.assert_called_once_with(test_user)
        # mock_jwt_usecase.create_access_token.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_onboarding_otp_invalid_otp_type(
        self,
        client: TestClient,
        mock_verify_otp_dep: MagicMock,
        test_otp_onboarding: Otp,
    ):
        # Mock OTP with a different type
        invalid_otp = test_otp_onboarding
        invalid_otp.otp_type = OtpType.PASSWORD_RESET  # Assign a different type

        mock_verify_otp_dep.return_value = invalid_otp

        response = client.post("/api/v1/verify/onbaording-otp")

        assert response.status_code == 400
        assert response.json()["message"] == "Invalid otp type"
        mock_verify_otp_dep.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_onboarding_otp_user_not_found(
        self,
        client: TestClient,
        mock_verify_otp_dep: MagicMock,
        mock_user_usecases: MagicMock,
        test_otp_onboarding: Otp,
    ):
        mock_verify_otp_dep.return_value = test_otp_onboarding
        mock_user_usecases.get_user_by_email.return_value = (None, NotFoundError)

        response = client.post("/api/v1/verify/onbaording-otp")

        assert response.status_code == 404
        assert response.json()["message"] == "user not found"
        mock_verify_otp_dep.assert_called_once()
        mock_user_usecases.get_user_by_email.assert_called_once_with(
            user_email=test_otp_onboarding.user_email
        )

    @pytest.mark.asyncio
    async def test_verify_onboarding_otp_user_save_fails(
        self,
        client: TestClient,
        mock_verify_otp_dep: MagicMock,
        mock_user_usecases: MagicMock,
        test_otp_onboarding: Otp,
        test_user: User,
    ):
        mock_verify_otp_dep.return_value = test_otp_onboarding
        mock_user_usecases.get_user_by_email.return_value = (test_user, None)
        mock_user_usecases.save.return_value = (None, Error("Database error"))

        response = client.post("/api/v1/verify/onbaording-otp")

        assert response.status_code == 404
        assert response.json()["message"] == "user not found"
        mock_verify_otp_dep.assert_called_once()
        mock_user_usecases.get_user_by_email.assert_called_once_with(
            user_email=test_otp_onboarding.user_email
        )
        assert test_user.is_email_verified is True
        mock_user_usecases.save.assert_called_once_with(test_user)
