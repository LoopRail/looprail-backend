from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import (
    get_jwt_usecase,
    get_otp_usecase,
    get_session_usecase,
    get_user_usecases,
    get_wallet_manager_usecase,
)
from src.main import app
from src.models import User
from src.usecases import JWTUsecase, OtpUseCase, SessionUseCase, UserUseCase


@pytest.fixture(name="client")
def client_fixture():
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="test_user")
def test_user_fixture() -> tuple[User, str]:
    user_id = uuid4()
    mock_user = User(
        id=user_id,
        email="test@example.com",
        first_name="Test",
        last_name="User",
        is_email_verified=True,
        has_completed_onboarding=True,
        username="testuser",
        wallet_address="0xMockWalletAddress",
    )
    password = "testpassword"
    return mock_user, password


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
def mock_session_usecase() -> MagicMock:
    mock = MagicMock(spec=SessionUseCase)
    app.dependency_overrides[get_session_usecase] = lambda: mock
    yield mock
    app.dependency_overrides.clear()


@pytest.fixture
def mock_jwt_usecase() -> MagicMock:
    mock = MagicMock(spec=JWTUsecase)
    app.dependency_overrides[get_jwt_usecase] = lambda: mock
    yield mock
    app.dependency_overrides.clear()


@pytest.fixture
def mock_wallet_manager_factory() -> MagicMock:
    mock = MagicMock()
    app.dependency_overrides[get_wallet_manager_usecase] = lambda: mock
    yield mock
    app.dependency_overrides.clear()