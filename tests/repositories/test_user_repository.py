"""
Tests for UserRepository using the SQLite test database.
Tests real DB operations + edge cases.
"""
import pytest
from uuid import uuid4

from src.infrastructure.repositories.user_repository import UserRepository
from src.models.user_model import User, UserCredentials, UserProfile
from src.types.error import NotFoundError, UserAlreadyExistsError
from src.types.types import Gender


# ─── Helpers ────────────────────────────────────────────────────────────────

def make_user(
    email="test@example.com",
    username="testuser",
    phone="+2348012345678",
    password_hash="hashed_pw",
) -> User:
    return User(
        id=uuid4(),
        email=email,
        username=username,
        first_name="Test",
        last_name="User",
        gender=Gender.MALE,
        is_active=True,
        is_email_verified=False,
        has_completed_onboarding=False,
        ledger_identity_id=f"temp_idty_{uuid4()}",
        credentials=UserCredentials(password_hash=password_hash),
        profile=UserProfile(phone_number=phone, country="Nigeria"),
    )


@pytest.fixture
def user_repo(test_db_session):
    return UserRepository(session=test_db_session)


# ─── create_user ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_user_success(user_repo):
    user = make_user()
    created, err = await user_repo.create_user(user=user)
    assert err is None
    assert created is not None
    assert created.email == user.email


@pytest.mark.asyncio
async def test_create_user_duplicate_email(user_repo):
    user = make_user(email="dup@example.com", username="unique1")
    await user_repo.create_user(user=user)

    user2 = make_user(email="dup@example.com", username="unique2")
    _, err = await user_repo.create_user(user=user2)
    assert isinstance(err, UserAlreadyExistsError)


@pytest.mark.asyncio
async def test_create_user_duplicate_username(user_repo):
    user = make_user(email="unique1@example.com", username="sameuser")
    await user_repo.create_user(user=user)

    user2 = make_user(email="unique2@example.com", username="sameuser")
    _, err = await user_repo.create_user(user=user2)
    assert isinstance(err, UserAlreadyExistsError)


# ─── get_user_by_id ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_user_by_id_found(user_repo):
    user = make_user()
    created, _ = await user_repo.create_user(user=user)

    found, err = await user_repo.get_user_by_id(user_id=created.id)
    assert err is None
    assert found is not None
    assert found.id == created.id


@pytest.mark.asyncio
async def test_get_user_by_id_not_found(user_repo):
    found, err = await user_repo.get_user_by_id(user_id=uuid4())
    assert err is None
    assert found is None


# ─── get_user_by_email ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_user_by_email_found(user_repo):
    user = make_user(email="unique_email@example.com")
    await user_repo.create_user(user=user)

    found, err = await user_repo.get_user_by_email(email="unique_email@example.com")
    assert err is None
    assert found is not None
    assert found.email == "unique_email@example.com"


@pytest.mark.asyncio
async def test_get_user_by_email_not_found(user_repo):
    found, err = await user_repo.get_user_by_email(email="no@one.com")
    assert err is None
    assert found is None


# ─── get_user_by_username ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_user_by_username_found(user_repo):
    user = make_user(email="usrnm@example.com", username="findme")
    await user_repo.create_user(user=user)

    found, err = await user_repo.get_user_by_username(username="findme")
    assert err is None
    assert found is not None
    assert found.username == "findme"


@pytest.mark.asyncio
async def test_get_user_by_username_not_found(user_repo):
    found, err = await user_repo.get_user_by_username(username="ghost")
    assert err is None
    assert found is None


# ─── list_users ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_users_returns_results(user_repo):
    await user_repo.create_user(user=make_user(email="a@a.com", username="a", phone="+2348000000001"))
    await user_repo.create_user(user=make_user(email="b@b.com", username="b", phone="+2348000000002"))

    users, err = await user_repo.list_users(limit=10)
    assert err is None
    assert len(users) >= 2


@pytest.mark.asyncio
async def test_list_users_pagination(user_repo):
    for i in range(3):
        await user_repo.create_user(
            user=make_user(
                email=f"page{i}@example.com",
                username=f"pageuser{i}",
                phone=f"+234800{1000+i}",
            )
        )

    page1, _ = await user_repo.list_users(limit=2, offset=0)
    page2, _ = await user_repo.list_users(limit=2, offset=2)
    assert len(page1) == 2
    assert len(page2) >= 1


# ─── update_user ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_user(user_repo):
    user = make_user(email="upd@example.com", username="upduser")
    created, _ = await user_repo.create_user(user=user)

    updated, err = await user_repo.update_user(user_id=created.id, first_name="NewName")
    assert err is None
    assert updated is not None
    assert updated.first_name == "NewName"


# ─── get_user_profile_by_phone_number ───────────────────────────────────────

@pytest.mark.asyncio
async def test_get_user_profile_by_phone_found(user_repo):
    user = make_user(email="phone@example.com", username="phoneuser", phone="+2348099999999")
    await user_repo.create_user(user=user)

    profile, err = await user_repo.get_user_profile_by_user_phone_number(phone_number="+2348099999999")
    assert err is None
    assert profile is not None
    assert profile.phone_number == "+2348099999999"


@pytest.mark.asyncio
async def test_get_user_profile_by_phone_not_found(user_repo):
    _, err = await user_repo.get_user_profile_by_user_phone_number(phone_number="+0000000000")
    assert err is not None  # Should return NotFoundError
