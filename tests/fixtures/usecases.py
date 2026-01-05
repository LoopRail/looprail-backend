from unittest.mock import AsyncMock, MagicMock

import pytest

from src.api.dependencies import get_otp_usecase, get_user_usecases
from src.main import app


@pytest.fixture
def mock_user_usecases():
    mock = MagicMock()
    app.dependency_overrides[get_user_usecases] = lambda: mock
    yield mock
    app.dependency_overrides.clear()


@pytest.fixture
def mock_otp_usecase():
    mock = MagicMock()

    mock.get_otp = AsyncMock()
    mock.delete_otp = AsyncMock()
    mock.verify_otp = AsyncMock()
    mock.verify_code = AsyncMock()
    mock.update_otp = AsyncMock()

    app.dependency_overrides[get_otp_usecase] = lambda: mock

    yield mock

    app.dependency_overrides.clear()
