import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import status
from uuid import UUID, uuid4
from datetime import datetime

from src.models import User, Session, RefreshToken
from src.types import AccessToken, TokenType, AccessTokenSub, RefreshTokenId, UserId
from src.usecases.security_usecases import AuthChallenge

@pytest.mark.asyncio
async def test_create_challenge_success(client, mock_security_usecase):
    challenge_id = "chl_test"
    nonce = "nonce_test"
    mock_security_usecase.create_challenge.return_value = (
        AuthChallenge(challenge_id=challenge_id, code_challenge="cc_test", nonce=nonce),
        None
    )
    
    response = client.post(
        "/api/v1/auth/challenge",
        json={"code_challenge": "cc_test"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["challenge-id"] == challenge_id
    assert response.json()["nonce"] == nonce

@pytest.mark.asyncio
async def test_set_passcode_success(client, mock_session_usecase, test_user_obj):
    # Mock authentication
    from src.api.dependencies import get_current_session
    from src.main import app
    
    session_id = str(uuid4())
    mock_session = MagicMock(spec=Session)
    mock_session.id = UUID(session_id)
    mock_session.get_prefixed_id.return_value = f"ses_{session_id}"
    
    # Override get_current_session as it's easier than mocking the whole JWT flow here
    app.dependency_overrides[get_current_session] = lambda: mock_session
    
    mock_session_usecase.set_passcode.return_value = None
    
    response = client.post(
        "/api/v1/auth/passcode/set",
        json={"passcode": "123456"},
        headers={"Authorization": "Bearer valid_token"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Passcode set successfully"
    
    # Clean up override
    del app.dependency_overrides[get_current_session]

@pytest.mark.asyncio
async def test_passcode_login_success(client, mock_session_usecase, mock_security_usecase, mock_jwt_usecase):
    session_id = f"ses_{uuid4()}"
    mock_security_usecase.verify_pkce.return_value = (True, None)
    mock_session_usecase.verify_passcode.return_value = (True, None)
    
    mock_session = MagicMock(spec=Session)
    mock_session.id = uuid4()
    mock_session.user_id = uuid4()
    mock_session.get_prefixed_id.return_value = session_id
    mock_session_usecase.get_session.return_value = (mock_session, None)
    
    mock_session_usecase.get_valid_refresh_token.return_value = ("rft_test", None)
    mock_jwt_usecase.create_token.return_value = "access_token_test"
    
    response = client.post(
        "/api/v1/auth/passcode-login",
        json={
            "challenge_id": "chl_test",
            "code_verifier": "cv_test",
            "passcode": "123456"
        },
        headers={
            "X-Session-Id": session_id,
            "Platform": "ios",
            "Device-Id": "device_test"
        }
    )
    
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["access-token"] == "access_token_test"
    assert response.json()["refresh-token"] == "rft_test"
