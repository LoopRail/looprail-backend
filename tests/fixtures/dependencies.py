import pytest
from unittest.mock import MagicMock

from sqlmodel import Session

from src.infrastructure.repositories import RefreshTokenRepository
from src.usecases.session_usecases import SessionUseCase
from tests.mocks.mock_session_repository import MockSessionRepository


@pytest.fixture
def mock_session_repository(db_session: Session) -> MockSessionRepository:
    return MockSessionRepository(db_session)


@pytest.fixture
def mock_refresh_token_repository() -> MagicMock:
    return MagicMock(spec=RefreshTokenRepository)


@pytest.fixture
def get_session_usecase_override(
    mock_session_repository: MockSessionRepository,
    mock_refresh_token_repository: MagicMock,
) -> SessionUseCase:
    return SessionUseCase(mock_session_repository, mock_refresh_token_repository)
