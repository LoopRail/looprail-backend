import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.dtos.user_dtos import UserCreate
from src.infrastructure.repositories.user_repository import UserRepository
from src.models.user_model import User
from src.usecases.user_usecases import UserUseCase
from src.types.types import Gender
from pydantic_extra_types.country import CountryShortName

@pytest.fixture
def user_repo(test_db_session):
    return UserRepository(session=test_db_session)

@pytest.fixture
def user_usecase(user_repo, mock_config, mock_wallet_manager_factory, mock_redis_service):
    # Mock Argon2 config and BlockRader config
    argon2_config_mock = MagicMock()
    argon2_config_mock.time_cost = 2
    argon2_config_mock.memory_cost = 1000 # reduced for faster tests
    argon2_config_mock.parallelism = 8
    argon2_config_mock.hash_len = 16
    argon2_config_mock.salt_len = 16

    blockrader_config_mock = MagicMock()

    usecase = UserUseCase(
        repo=user_repo,
        blockrader_config=blockrader_config_mock,
        argon2_config=argon2_config_mock,
        wallet_manager_usecase=mock_wallet_manager_factory,
        wallet_service=AsyncMock(),
        cache_service=mock_redis_service
    )
    # Ensure cache miss by default for tests to hit DB
    usecase.cache.get = AsyncMock(return_value=None)
    usecase.cache.set = AsyncMock(return_value=None)
    usecase.cache.delete = AsyncMock(return_value=None)
    return usecase

@pytest.mark.asyncio
async def test_create_user_success(user_usecase, test_db_session):
    # Arrange
    user_data = UserCreate(
        email="newuser@example.com",
        password="StrongPassword123!",
        first_name="John",
        last_name="Doe",
        username="johndoe",
        country_code="Nigeria",
        phone_number="+2348012345678",
        gender=Gender.MALE
    )

    # Act
    result_user, err = await user_usecase.create_user(user_data)

    # Assert
    assert err is None
    assert result_user is not None
    assert result_user.email == "newuser@example.com"
    assert result_user.username == "johndoe"

    
    # Verify DB persistence
    db_user, err = await user_usecase.get_user_by_id(result_user.id)
    assert err is None
    assert db_user is not None
    assert db_user.email == user_data.email

@pytest.mark.asyncio
async def test_setup_user_wallet_success(user_usecase, test_db_session):
    # Arrange: Create a real user in the DB first
    user_data = UserCreate(
        email="walletuser@example.com",
        password="StrongPassword123!",
        first_name="Wallet",
        last_name="User",
        username="walletuser",
        country_code="Nigeria",
        phone_number="+2348098765432",
        gender=Gender.MALE
    )
    user, err = await user_usecase.create_user(user_data)
    assert err is None
    
    transaction_pin = "1234"

    # Mock external wallet service behavior
    mock_ledger_identity = MagicMock()
    mock_ledger_identity.identity_id = "real_ledger_id_456"
    user_usecase.wallet_service.create_ledger_identity.return_value = (mock_ledger_identity, None)
    user_usecase.wallet_manager_usecase.create_user_wallet.return_value = (MagicMock(), None)

    # Act
    updated_user, err = await user_usecase.setup_user_wallet(user_id=user.id, transaction_pin=transaction_pin)

    # Assert
    assert err is None
    assert updated_user is not None
    assert updated_user.ledger_identity_id == "real_ledger_id_456"
    
    # Verify the external service calls
    user_usecase.wallet_service.create_ledger_identity.assert_called_once()
    user_usecase.wallet_manager_usecase.create_user_wallet.assert_called_once_with(user.id)

    # Verify DB persistence for the updates
    db_user, err = await user_usecase.get_user_by_id(user.id)
    assert err is None
    assert db_user.ledger_identity_id == "real_ledger_id_456"
