"""
Tests for SessionRepository and RefreshTokenRepository using the SQLite test database.
"""
import hashlib
import pytest
import pytest_asyncio
from uuid import uuid4

from src.infrastructure.repositories.refresh_token_repository import RefreshTokenRepository
from src.infrastructure.repositories.session_repository import SessionRepository
from src.infrastructure.repositories.user_repository import UserRepository
from src.models.user_model import User, UserCredentials, UserProfile
from src.types.types import Gender


# ─── Helpers ────────────────────────────────────────────────────────────────

def make_user(email="sess@example.com", username="sessuser", phone="+2348012000001") -> User:
    return User(
        id=uuid4(),
        email=email,
        username=username,
        first_name="Session",
        last_name="Test",
        gender=Gender.MALE,
        is_active=True,
        ledger_identity_id=f"temp_idty_{uuid4()}",
        credentials=UserCredentials(password_hash="hashed"),
        profile=UserProfile(phone_number=phone, country="Nigeria"),
    )


@pytest.fixture
def session_repo(test_db_session):
    return SessionRepository(session=test_db_session)


@pytest.fixture
def refresh_token_repo(test_db_session):
    return RefreshTokenRepository(session=test_db_session)


@pytest.fixture
def user_repo(test_db_session):
    return UserRepository(session=test_db_session)


@pytest_asyncio.fixture
async def db_user(user_repo):
    """Create and persist a test user in the DB."""
    user, _ = await user_repo.create_user(user=make_user())
    return user


# ─── create_session ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_session_success(session_repo, db_user):
    session, err = await session_repo.create_session(
        user_id=db_user.id,
        platform="ios",
        device_id="device_001",
        ip_address="127.0.0.1",
    )
    assert err is None
    assert session is not None
    assert session.user_id == db_user.id
    assert session.platform == "ios"
    assert session.revoked_at is None


# ─── get_session ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_session_found(session_repo, db_user):
    session, _ = await session_repo.create_session(
        user_id=db_user.id,
        platform="android",
        device_id="device_002",
        ip_address="127.0.0.1",
    )

    found, err = await session_repo.get_session(session.id)
    assert err is None
    assert found is not None
    assert found.id == session.id


@pytest.mark.asyncio
async def test_get_session_not_found(session_repo):
    found, err = await session_repo.get_session(uuid4())
    # Should return None, None (not found but no error raised)
    assert found is None


# ─── revoke_session ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_revoke_session(session_repo, db_user):
    session, _ = await session_repo.create_session(
        user_id=db_user.id,
        platform="web",
        device_id="device_003",
        ip_address="127.0.0.1",
    )

    err = await session_repo.revoke_session(session.id)
    assert err is None

    # Revoked sessions are not returned by get_session
    found, _ = await session_repo.get_session(session.id)
    assert found is None


# ─── get_active_sessions_ordered ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_active_sessions_ordered(session_repo, db_user):
    for i in range(3):
        await session_repo.create_session(
            user_id=db_user.id,
            platform="ios",
            device_id=f"device_{i}",
            ip_address="127.0.0.1",
        )

    sessions = await session_repo.get_active_sessions_ordered(db_user.id)
    assert len(sessions) == 3
    # They should be ordered oldest first
    for i in range(len(sessions) - 1):
        assert sessions[i].last_seen_at <= sessions[i + 1].last_seen_at


# ─── revoke_all_user_sessions ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_revoke_all_user_sessions(session_repo, db_user):
    for i in range(2):
        await session_repo.create_session(
            user_id=db_user.id,
            platform="ios",
            device_id=f"device_{i}",
            ip_address="127.0.0.1",
        )

    err = await session_repo.revoke_all_user_sessions(db_user.id)
    assert err is None

    remaining = await session_repo.get_user_sessions(db_user.id)
    assert len(remaining) == 0


# ─── RefreshTokenRepository ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_refresh_token(session_repo, refresh_token_repo, db_user):
    session, _ = await session_repo.create_session(
        user_id=db_user.id,
        platform="ios",
        device_id="device_10",
        ip_address="127.0.0.1",
    )

    token_string = "some-random-token-string"
    token, err = await refresh_token_repo.create_refresh_token(
        session_id=session.id,
        new_refresh_token_string=token_string,
        expires_in_days=7,
    )
    assert err is None
    assert token is not None
    assert token.session_id == session.id


@pytest.mark.asyncio
async def test_get_valid_refresh_token_by_hash(session_repo, refresh_token_repo, db_user):
    session, _ = await session_repo.create_session(
        user_id=db_user.id,
        platform="ios",
        device_id="device_11",
        ip_address="127.0.0.1",
    )
    token_string = "fresh-token-string"
    token_hash = hashlib.sha256(token_string.encode()).hexdigest()

    await refresh_token_repo.create_refresh_token(
        session_id=session.id,
        new_refresh_token_string=token_string,
        expires_in_days=7,
    )

    found, err = await refresh_token_repo.get_valid_refresh_token_by_hash(token_hash)
    assert err is None
    assert found is not None
    assert found.token_hash == token_hash


@pytest.mark.asyncio
async def test_get_valid_refresh_token_not_found(refresh_token_repo):
    _, err = await refresh_token_repo.get_valid_refresh_token_by_hash("badhash")
    assert err is not None


@pytest.mark.asyncio
async def test_revoke_refresh_tokens_for_session(session_repo, refresh_token_repo, db_user):
    session, _ = await session_repo.create_session(
        user_id=db_user.id,
        platform="ios",
        device_id="device_12",
        ip_address="127.0.0.1",
    )

    await refresh_token_repo.create_refresh_token(
        session_id=session.id,
        new_refresh_token_string="token-to-revoke",
        expires_in_days=7,
    )

    err = await refresh_token_repo.revoke_refresh_tokens_for_session(session.id)
    assert err is None

    # Token should no longer be valid
    token_hash = hashlib.sha256("token-to-revoke".encode()).hexdigest()
    _, err2 = await refresh_token_repo.get_valid_refresh_token_by_hash(token_hash)
    assert err2 is not None
