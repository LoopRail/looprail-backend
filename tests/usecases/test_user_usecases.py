import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.dtos.user_dtos import UserCreate
from src.infrastructure.repositories.user_repository import UserRepository
from src.models.user_model import User
from src.usecases.user_usecases import UserUseCase
from src.types.types import Gender

@pytest.fixture
def mock_user_repo():
    repo = AsyncMock(spec=UserRepository)
    return repo

@pytest.fixture
def user_usecase(mock_user_repo, mock_config, mock_wallet_manager_factory, mock_redis_service):
    # Mock Argon2 config and BlockRader config
    argon2_config_mock = MagicMock()
    argon2_config_mock.time_cost = 2
    argon2_config_mock.memory_cost = 102400
    argon2_config_mock.parallelism = 8
    argon2_config_mock.hash_len = 16
    argon2_config_mock.salt_len = 16

    blockrader_config_mock = MagicMock()

    usecase = UserUseCase(
        repo=mock_user_repo,
        blockrader_config=blockrader_config_mock,
        argon2_config=argon2_config_mock,
        wallet_manager_usecase=mock_wallet_manager_factory,
        wallet_service=AsyncMock(),
        cache_service=mock_redis_service
    )
    return usecase

@pytest.mark.asyncio
async def test_create_user_success(user_usecase, mock_user_repo):
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

    # Mock the phone number check to return None (no existing profile)
    mock_user_repo.get_user_profile_by_user_phone_number.return_value = (None, None)

    # Mock the creation process
    created_user_id = uuid4()
    mock_created_user = User(
        id=created_user_id,
        email=user_data.email,
        username=user_data.username,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        gender=user_data.gender,
        ledger_identity_id="temp_idty_123"
    )
    mock_user_repo.create_user.return_value = (mock_created_user, None)

    # Act
    result_user, err = await user_usecase.create_user(user_data)

    # Assert
    assert err is None
    assert result_user is not None
    assert result_user.email == "newuser@example.com"
    assert result_user.username == "johndoe"
    
    # Verify repository calls
    mock_user_repo.create_user.assert_called_once()
    
    # Assert creating user argument
    call_args = mock_user_repo.create_user.call_args
    assert "user" in call_args.kwargs
    passed_user = call_args.kwargs["user"]
    assert passed_user.email == user_data.email
    assert passed_user.username == user_data.username
    assert passed_user.profile.phone_number == user_data.phone_number
    assert passed_user.credentials.password_hash is not None
