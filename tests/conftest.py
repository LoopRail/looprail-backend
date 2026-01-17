from unittest.mock import MagicMock
from uuid import uuid4
import os

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from src.api.dependencies import (
    get_config,
    get_jwt_usecase,
    get_otp_usecase,
    get_otp_token,
    get_session_usecase,  # Re-added this import
    get_user_usecases,
    get_wallet_manager_usecase,
)
from src.infrastructure.config_settings import Config
from src.infrastructure.settings import JWTConfig
from src.infrastructure.db import get_session as get_app_session
from src.main import app
from src.models import Otp, User
from src.types import OtpType
from src.usecases import JWTUsecase, OtpUseCase, SessionUseCase, UserUseCase
from src.infrastructure.config_settings import load_config
import time


os.environ["ENVIRONMENT"] = "test"
# Load the test config immediately to ensure it's used by subsequent imports
_ = load_config()


@pytest.fixture(name="test_db_session")
async def test_db_session_fixture():
    # We need a new engine for the test database to avoid conflicts
    # with the application's engine if it were to be initialized.
    # The get_uri() from load_config() now correctly points to sqlite+aiosqlite:///./test.db
    test_db_url = load_config().database.get_uri()

    engine = create_async_engine(test_db_url, echo=False)

    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)

    await engine.dispose()


import httpx
from fastapi.testclient import TestClient  # Add TestClient import


@pytest.fixture(name="client")
def client_fixture(
    test_db_session: AsyncSession,
):  # Keep test_db_session for now, will address later
    app.dependency_overrides[get_app_session] = lambda: test_db_session
    with TestClient(app=app) as client:  # Use TestClient for synchronous testing
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
def mock_get_otp_token() -> MagicMock:
    mock = MagicMock(return_value="dummy_otp_token")
    app.dependency_overrides[get_otp_token] = lambda: mock
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
