import os

os.environ["ENVIRONMENT"] = "test"

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB
from src.main import app

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

from src.infrastructure.config_settings import load_config

# Load the test config immediately to ensure it's used by subsequent imports
test_config = load_config()

from src.dtos.base import Base as DTOBase

DTOBase.dto_config = {
    "disposable_email_domains": test_config.disposable_email_domains,
    "allowed_countries": test_config.countries,
}

from src.api.dependencies import (
    get_config,
    get_jwt_usecase,
    get_otp_usecase,
    get_otp_token,
    get_security_usecase,
    get_session_usecase,
    get_user_usecases,
    get_wallet_manager_usecase,
)
from src.api.dependencies.services import get_redis_service, get_resend_service
from src.infrastructure.settings import ENVIRONMENT, JWTConfig
from src.main import app
from src.models import Otp, User
from src.types import OtpType
from src.usecases import (
    JWTUsecase,
    OtpUseCase,
    SecurityUseCase,
    SessionUseCase,
    UserUseCase,
)
import time


import pytest_asyncio

@pytest_asyncio.fixture(name="test_db_session")
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


from fastapi.testclient import TestClient  # Add TestClient import


@pytest.fixture(name="client")
def client_fixture():
    with TestClient(app=app) as client:
        yield client


@pytest.fixture(name="test_user")
def test_user_fixture() -> tuple[User, str]:
    user_id = uuid4()
    mock_user = User(
        id=user_id,
        email="test@example.com",
        first_name="Test",
        last_name="User",
        is_email_verified=False,
        has_completed_onboarding=True,
        username="testuser",
        gender="male",
    )
    password = "testpassword123"
    return mock_user, password


@pytest.fixture(name="test_user_obj")
def test_user_obj_fixture(test_user: tuple[User, str]) -> User:
    return test_user[0]


@pytest.fixture
def mock_user_usecases(test_user_obj: User) -> MagicMock:
    mock = AsyncMock(spec=UserUseCase)
    mock.get_user_by_email.return_value = (test_user_obj, None)
    mock.authenticate_user.return_value = (None, None)
    mock.create_user.return_value = (None, None)
    mock.get_user_by_id.return_value = (None, None)
    mock.load_public_user.return_value = (None, None)
    app.dependency_overrides[get_user_usecases] = lambda: mock
    yield mock
    if get_user_usecases in app.dependency_overrides:
        del app.dependency_overrides[get_user_usecases]


@pytest.fixture
def mock_otp_usecase() -> MagicMock:
    mock = AsyncMock(spec=OtpUseCase)
    mock.update_otp.return_value = None
    mock.delete_otp.return_value = None
    app.dependency_overrides[get_otp_usecase] = lambda: mock
    yield mock
    if get_otp_usecase in app.dependency_overrides:
        del app.dependency_overrides[get_otp_usecase]


@pytest.fixture
def mock_session_usecase() -> MagicMock:
    mock = AsyncMock(spec=SessionUseCase)
    mock.create_session.return_value = (MagicMock(), "mock_raw_refresh_token", None)
    mock.get_session.return_value = (None, None)
    mock.rotate_refresh_token.return_value = None
    mock.get_valid_refresh_token_by_hash.return_value = (None, None)
    mock.verify_passcode.return_value = (True, None)
    app.dependency_overrides[get_session_usecase] = lambda: mock
    yield mock
    if get_session_usecase in app.dependency_overrides:
        del app.dependency_overrides[get_session_usecase]


@pytest.fixture
def mock_jwt_usecase() -> MagicMock:
    mock = MagicMock(spec=JWTUsecase)
    app.dependency_overrides[get_jwt_usecase] = lambda: mock
    yield mock
    if get_jwt_usecase in app.dependency_overrides:
        del app.dependency_overrides[get_jwt_usecase]


@pytest.fixture
def mock_security_usecase() -> AsyncMock:
    mock = AsyncMock(spec=SecurityUseCase)
    mock.create_challenge.return_value = (None, None)
    mock.verify_pkce.return_value = (True, None)
    app.dependency_overrides[get_security_usecase] = lambda: mock
    yield mock
    if get_security_usecase in app.dependency_overrides:
        del app.dependency_overrides[get_security_usecase]


@pytest.fixture
def mock_wallet_manager_factory() -> MagicMock:
    mock = AsyncMock()  # WalletManager probably async
    app.dependency_overrides[get_wallet_manager_usecase] = lambda: mock
    yield mock
    if get_wallet_manager_usecase in app.dependency_overrides:
        del app.dependency_overrides[get_wallet_manager_usecase]


@pytest.fixture(autouse=True)
def mock_config() -> MagicMock:
    mock_jwt_settings = MagicMock(spec=JWTConfig)
    mock_jwt_settings.onboarding_token_expire_minutes = 15
    mock_jwt_settings.access_token_expire_minutes = 60
    mock_jwt_settings.secret_key = "test_secret_key"
    mock_jwt_settings.algorithm = "HS256"
    mock_jwt_settings.refresh_token_expires_in_days = 7

    mock = MagicMock()
    mock.jwt = mock_jwt_settings
    mock.disposable_email_domains = []
    mock.countries = MagicMock()
    mock.app = MagicMock()
    mock.app.environment = ENVIRONMENT.TEST

    app.dependency_overrides[get_config] = lambda: mock
    yield mock
    if get_config in app.dependency_overrides:
        del app.dependency_overrides[get_config]


@pytest.fixture
def mock_get_otp_token() -> MagicMock:
    mock = MagicMock(return_value="dummy_otp_token")
    app.dependency_overrides[get_otp_token] = lambda: mock
    yield mock
    if get_otp_token in app.dependency_overrides:
        del app.dependency_overrides[get_otp_token]


@pytest.fixture(autouse=True)
def mock_redis_service() -> AsyncMock:
    mock = AsyncMock()
    # Configure all methods as AsyncMocks
    for method in ['get', 'set', 'delete', 'zcard', 'incr', 'zremrangebyscore', 'zadd', 'zrange', 'expire', 'hgetall', 'hset', 'ping']:
        setattr(mock, method, AsyncMock())
    
    # Set default return values
    mock.get.return_value = None
    mock.zcard.return_value = 0
    mock.incr.return_value = 0
    mock.hgetall.return_value = {}
    mock.ping.return_value = True

    # CRITICAL: _instance must be the mock itself (or an AsyncMock)
    mock._instance = mock
    
    # Ensure app.state.redis is also this mock for decorators
    app.state.redis = mock
    
    app.dependency_overrides[get_redis_service] = lambda: mock
    return mock


@pytest.fixture(autouse=True)
def mock_redis_client_class(mock_redis_service):
    with patch("src.main.RedisClient") as mock_class:
        mock_class.return_value = mock_redis_service
        yield mock_class


@pytest.fixture(autouse=True)
def mock_resend_service() -> AsyncMock:
    from src.infrastructure.services import ResendService
    mock = AsyncMock(spec=ResendService)
    mock.send.return_value = ({"id": "test-id"}, None)
    mock.default_sender_domain = "looprail.xyz"
    app.dependency_overrides[get_resend_service] = lambda: mock
    yield mock
    if get_resend_service in app.dependency_overrides:
        del app.dependency_overrides[get_resend_service]


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


@pytest.fixture(autouse=True)
def mock_redis_client_class():
    with patch("src.main.RedisClient") as mock:
        yield mock
