"""
Extended tests for UserUseCase covering all major flows:
- create_user
- setup_user_wallet
- authenticate_user
- finalize_onboarding
- update_transaction_pin
- get_user_by_id
Edge cases are tested explicitly.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.dtos.user_dtos import UserCreate
from src.infrastructure.repositories.user_repository import UserRepository
from src.models.user_model import User, UserCredentials, UserProfile
from src.usecases.user_usecases import UserUseCase
from src.types.types import Gender
from src.types.error import InvalidCredentialsError, UserAlreadyExistsError


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def user_repo(test_db_session):
    return UserRepository(session=test_db_session)


@pytest.fixture
def user_usecase(user_repo, mock_config, mock_wallet_manager_factory, mock_redis_service):
    argon2_config_mock = MagicMock()
    argon2_config_mock.time_cost = 2
    argon2_config_mock.memory_cost = 1000
    argon2_config_mock.parallelism = 8
    argon2_config_mock.hash_len = 16
    argon2_config_mock.salt_len = 16

    usecase = UserUseCase(
        repo=user_repo,
        blockrader_config=MagicMock(),
        argon2_config=argon2_config_mock,
        wallet_manager_usecase=mock_wallet_manager_factory,
        wallet_service=AsyncMock(),
        cache_service=mock_redis_service,
    )
    usecase.cache.get = AsyncMock(return_value=None)
    usecase.cache.set = AsyncMock(return_value=None)
    usecase.cache.delete = AsyncMock(return_value=None)
    return usecase


def default_user_data(**overrides) -> UserCreate:
    kwargs = dict(
        email="newuser@example.com",
        password="StrongPassword123!",
        first_name="John",
        last_name="Doe",
        username="johndoe",
        country_code="Nigeria",
        phone_number="+2348012345678",
        gender=Gender.MALE,
    )
    kwargs.update(overrides)
    return UserCreate(**kwargs)


# ─── create_user ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_user_success(user_usecase, test_db_session):
    user_data = default_user_data()
    result_user, err = await user_usecase.create_user(user_data)

    assert err is None
    assert result_user is not None
    assert result_user.email == user_data.email
    assert result_user.username == user_data.username

    # DB persistence check
    db_user, _ = await user_usecase.get_user_by_id(result_user.id)
    assert db_user is not None
    assert db_user.email == user_data.email


@pytest.mark.asyncio
async def test_create_user_duplicate_phone(user_usecase):
    """Creating two users with the same phone number should fail on second attempt."""
    await user_usecase.create_user(default_user_data(
        email="first@example.com",
        username="firstuser",
        phone_number="+2348012345678",
    ))
    _, err = await user_usecase.create_user(default_user_data(
        email="second@example.com",
        username="seconduser",
        phone_number="+2348012345678",
    ))
    assert err is not None  # UserAlreadyExistsError or similar


@pytest.mark.asyncio
async def test_create_user_duplicate_email(user_usecase):
    await user_usecase.create_user(default_user_data(
        email="dup@example.com",
        username="dupuser1",
        phone_number="+2348011111111",
    ))
    _, err = await user_usecase.create_user(default_user_data(
        email="dup@example.com",
        username="dupuser2",
        phone_number="+2348022222222",
    ))
    assert err is not None


# ─── authenticate_user ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_authenticate_user_success(user_usecase):
    user_data = default_user_data(email="auth@example.com", username="authuser", phone_number="+2348033333333")
    created, _ = await user_usecase.create_user(user_data)
    assert created is not None

    authenticated, err = await user_usecase.authenticate_user(
        email=user_data.email,
        password=user_data.password,
    )
    assert err is None
    assert authenticated is not None
    assert authenticated.email == user_data.email


@pytest.mark.asyncio
async def test_authenticate_user_wrong_password(user_usecase):
    user_data = default_user_data(email="wrongpw@example.com", username="wrongpwuser", phone_number="+2348044444444")
    await user_usecase.create_user(user_data)

    _, err = await user_usecase.authenticate_user(
        email=user_data.email,
        password="WrongPassword!",
    )
    assert err is not None


@pytest.mark.asyncio
async def test_authenticate_user_nonexistent_email(user_usecase):
    _, err = await user_usecase.authenticate_user(
        email="ghost@example.com",
        password="anything",
    )
    assert err is not None


# ─── setup_user_wallet ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_setup_user_wallet_success(user_usecase, test_db_session):
    user_data = default_user_data(email="walletuser@example.com", username="walletuser", phone_number="+2348098765432")
    user, _ = await user_usecase.create_user(user_data)
    assert user is not None

    # Mock external services
    mock_ledger = MagicMock()
    mock_ledger.identity_id = "real_ledger_id_456"
    user_usecase.wallet_service.create_ledger_identity.return_value = (mock_ledger, None)
    user_usecase.wallet_manager_usecase.create_user_wallet.return_value = (MagicMock(), None)

    updated, err = await user_usecase.setup_user_wallet(user_id=user.id, transaction_pin="1234")

    assert err is None
    assert updated is not None
    assert updated.ledger_identity_id == "real_ledger_id_456"

    # Verify external service was called
    user_usecase.wallet_service.create_ledger_identity.assert_called_once()
    user_usecase.wallet_manager_usecase.create_user_wallet.assert_called_once_with(user.id)


@pytest.mark.asyncio
async def test_setup_user_wallet_ledger_failure(user_usecase):
    """If wallet_service.create_ledger_identity fails, setup_user_wallet should propagate error."""
    from src.types.error import error as AppError
    user_data = default_user_data(email="wfail@example.com", username="walletfail", phone_number="+2348055555555")
    user, _ = await user_usecase.create_user(user_data)

    user_usecase.wallet_service.create_ledger_identity.return_value = (None, AppError("Ledger service down"))

    _, err = await user_usecase.setup_user_wallet(user_id=user.id, transaction_pin="5678")
    assert err is not None
    assert "Ledger service down" in err.message


# ─── finalize_onboarding ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_finalize_onboarding_success(user_usecase):
    user_data = default_user_data(email="onboard@example.com", username="onboarduser", phone_number="+2348066666666")
    user, _ = await user_usecase.create_user(user_data)

    updated, err = await user_usecase.finalize_onboarding(
        user_id=user.id,
        onboarding_responses=["response1", "response2"],
    )
    assert err is None
    assert updated is not None
    assert updated.has_completed_onboarding is True


# ─── update_transaction_pin ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_transaction_pin(user_usecase):
    user_data = default_user_data(email="pin@example.com", username="pinuser", phone_number="+2348077777777")
    user, _ = await user_usecase.create_user(user_data)

    updated, err = await user_usecase.update_transaction_pin(user_id=user.id, pin="9999")
    assert err is None
    assert updated is not None


# ─── get_user_by_id ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_user_by_id_not_found(user_usecase):
    found, err = await user_usecase.get_user_by_id(user_id=uuid4())
    # Should return None with no error (user simply doesn't exist)
    assert found is None


@pytest.mark.asyncio
async def test_get_user_by_id_cache_miss_hits_db(user_usecase):
    """Cache miss should fall through to DB."""
    user_data = default_user_data(email="cache@example.com", username="cacheuser", phone_number="+2348088888888")
    created, _ = await user_usecase.create_user(user_data)

    user_usecase.cache.get = AsyncMock(return_value=None)  # Force cache miss
    found, err = await user_usecase.get_user_by_id(created.id)
    assert err is None
    assert found is not None
    assert found.email == created.email
