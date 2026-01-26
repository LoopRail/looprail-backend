import uuid
from typing import List, Optional, Tuple

from pydantic_core import ValidationError

from src.dtos.user_dtos import UserCreate, UserPublic
from src.infrastructure.logger import get_logger
from src.infrastructure.repositories import UserRepository
from src.infrastructure.security import Argon2Config
from src.infrastructure.settings import BlockRaderConfig
from src.models import User, UserCredentials, UserPin, UserProfile
from src.types import (
    Error,
    HashedPassword,
    InvalidCredentialsError,
    NotFoundError,
    UserAlreadyExistsError,
    error,
)
from src.types.common_types import UserId
from src.usecases.wallet_usecases import WalletManagerUsecase, WalletService
from src.utils import hash_password, verify_password

logger = get_logger(__name__)


class UserUseCase:
    def __init__(
        self,
        repo: UserRepository,
        *,
        blockrader_config: BlockRaderConfig,
        argon2_config: Argon2Config,
        wallet_manager_usecase: WalletManagerUsecase,
        wallet_service: WalletService,
    ):
        self.repo = repo
        self.blockrader_config = blockrader_config
        self.argon2_config = argon2_config
        self.wallet_manager_usecase = wallet_manager_usecase
        self.wallet_service = wallet_service
        logger.debug("UserUseCase initialized.")

    async def authenticate_user(
        self, email: str, password: str
    ) -> Tuple[Optional[User], Error]:
        logger.debug("Authenticating user with email: %s", email)
        user, err = await self.repo.get_user_by_email(email=email)
        if err:
            logger.debug("Error getting user by email %s: %s", email, err.message)
            return None, err
        if not user:
            logger.warning(
                "Authentication failed: User with email %s not found.", email
            )
            return None, InvalidCredentialsError
        if not user.credentials:
            logger.warning("Authentication failed: User %s has no credentials.", email)
            return None, InvalidCredentialsError
        logger.debug("User %s found. Verifying password.", user.id)

        hashed_password_obj = HashedPassword(
            password_hash=user.credentials.password_hash
        )
        if not verify_password(password, hashed_password_obj, self.argon2_config):
            logger.warning(
                "Authentication failed: Invalid credentials for user %s", email
            )
            return None, InvalidCredentialsError
        logger.info("User %s authenticated successfully.", user.id)
        return user, None

    async def save(self, user: User) -> Tuple[Optional[User], Error]:
        logger.debug("Saving user with ID: %s", user.id)
        err = await self.repo.save(user)
        if err:
            logger.error("Failed to save user %s: %s", user.id, err.message)
        else:
            logger.info("User %s saved successfully.", user.id)
        return user, err

    async def update_user(
        self, user_id: UserId, /, **kwargs
    ) -> Tuple[Optional[User], Error]:
        logger.debug("Updating user %s with data: %s", user_id, kwargs)
        user, err = await self.repo.update_user(user_id=user_id, **kwargs)
        if err:
            logger.error("Failed to update user %s: %s", user_id, err.message)
        else:
            logger.info("User %s updated successfully.", user_id)
        return user, err

    async def update_user_profile(
        self, user_id: UserId, /, **kwargs
    ) -> Tuple[Optional[UserProfile], Error]:
        logger.debug("Updating user profile for user %s with data: %s", user_id, kwargs)
        user_profile, err = await self.repo.update_user_profile(user_id, **kwargs)
        if err:
            logger.error(
                "Failed to update user profile for user %s: %s", user_id, err.message
            )
        else:
            logger.info("User profile for user %s updated successfully.", user_id)
        return user_profile, err

    async def create_user(
        self, user_create: UserCreate
    ) -> Tuple[Optional[User], Error]:
        logger.debug("Creating new user with email: %s", user_create.email)
        temp_ledger_identity_id = f"temp_idty_{uuid.uuid4()}"
        logger.debug(
            "Generated temporary ledger identity ID: %s", temp_ledger_identity_id
        )

        existing_user_by_phone, err = await self.get_user_by_phone_number(
            phone_number=str(user_create.phone_number)
        )

        if err and err != NotFoundError:
            logger.error(
                "Failed to check for existing phone number for %s: %s",
                user_create.phone_number,
                err.message,
            )
            return None, err
        if existing_user_by_phone:
            return None, UserAlreadyExistsError(
                "User with this phone number already exists"
            )

        hashed_password_obj = hash_password(user_create.password, self.argon2_config)

        user_credentials = UserCredentials(
            password_hash=hashed_password_obj.password_hash
        )
        user_profile = UserProfile(
            phone_number=user_create.phone_number, country=user_create.country_code
        )
        user = User(
            email=user_create.email,
            first_name=user_create.first_name,
            last_name=user_create.last_name,
            gender=user_create.gender,
            ledger_identity_id=temp_ledger_identity_id,
            username=user_create.username,
            credentials=user_credentials,
            profile=user_profile,
        )

        created_user, err = await self.repo.create(user=user)
        if err:
            logger.error(
                "Failed to create user in repository for email %s: %s",
                user_create.email,
                err.message,
                exc_info=True,
            )
            return None, err
        logger.info(
            "User %s (ID: %s) created successfully with temporary ledger ID %s.",
            user_create.username,
            created_user.id,
            temp_ledger_identity_id,
        )

        return created_user, None

    async def setup_user_wallet(
        self,
        user_id: UserId,
        transaction_pin: str,
    ) -> Tuple[Optional[User], Error]:
        logger.info("Setting up wallet for user %s", user_id)

        user, err = await self.get_user_by_id(user_id)
        if err or not user:
            return None, err

        # 1. Update transaction pin
        user, err = await self.update_transaction_pin(user_id, transaction_pin)
        if err:
            return None, err

        # 2. Create ledger identity
        logger.debug("Creating ledger identity for user ID %s", user_id)
        ledger_identity, err = await self.wallet_service.create_ledger_identity(user)
        if err:
            logger.error(
                "Failed to create ledger identity for user ID %s: %s",
                user_id,
                err.message,
                exc_info=True,
            )
            return None, err

        user.ledger_identity_id = ledger_identity.identity_id

        logger.debug("Creating wallet for user ID %s", user_id)
        _, err = await self.wallet_manager_usecase.create_user_wallet(user.id)
        if err:
            logger.error(
                "Failed to create wallet for user ID %s: %s",
                user_id,
                err.message,
                exc_info=True,
            )
            return None, err

        updated_user, err = await self.save(user)
        if err:
            return None, err

        logger.info("Wallet setup successfully for user ID %s", user_id)
        return updated_user, None

    async def finalize_onboarding(
        self,
        user_id: UserId,
        onboarding_responses: List[str],
    ) -> Tuple[Optional[User], Error]:
        logger.info("Finalizing onboarding for user %s", user_id)

        user, err = await self.get_user_by_id(user_id)
        if err or not user:
            return None, err

        # 1. Store onboarding responses
        user.onboarding_responses = onboarding_responses

        # 2. Mark as completed
        user.has_completed_onboarding = True

        updated_user, err = await self.save(user)
        if err:
            return None, err

        logger.info("Onboarding completed successfully for user ID %s", user_id)
        return updated_user, None

    async def get_user_by_id(self, user_id: UserId) -> Tuple[Optional[User], Error]:
        logger.debug("Getting user by ID: %s", user_id)
        user, err = await self.repo.get_user_by_id(user_id=user_id)
        if err:
            logger.debug("User %s not found: %s", user_id, err.message)
        else:
            logger.debug("User %s retrieved.", user_id)
        return user, err

    async def get_user_by_email(self, user_email: str) -> Tuple[Optional[User], Error]:
        logger.debug("Getting user by email: %s", user_email)
        user, err = await self.repo.get_user_by_email(email=user_email)
        if err:
            logger.debug("User with email %s not found: %s", user_email, err.message)
        else:
            logger.debug("User with email %s retrieved.", user_email)
        return user, err

    async def get_user_by_phone_number(
        self, phone_number: str
    ) -> Tuple[Optional[User], Error]:
        logger.debug("Getting user by phone number: %s", phone_number)
        (
            user_profile,
            err,
        ) = await self.repo.get_user_profile_by_user_phone_number(
            phone_number=phone_number
        )
        if err:
            logger.debug(
                "User with phone number %s not found: %s", phone_number, err.message
            )
            return None, err
        if not user_profile:
            return None, None
        user, err = await self.repo.get_user_by_id(user_id=user_profile.user_id)
        if err:
            logger.error(
                "Could not retrieve user for profile with phone number %s: %s",
                phone_number,
                err.message,
            )
            return None, err
        logger.debug("User %s retrieved by phone number.", user.id)
        return user, None

    async def update_transaction_pin(
        self, user_id: UserId, pin: str
    ) -> Tuple[Optional[User], Error]:
        logger.debug("Updating transaction pin for user %s", user_id)

        user, err = await self.get_user_by_id(user_id)
        if err:
            return None, err

        hashed_pin = hash_password(pin, self.argon2_config)

        if user.pin:
            user.pin.pin_hash = hashed_pin.password_hash
        else:
            user.pin = UserPin(pin_hash=hashed_pin.password_hash)

        updated_user, err = await self.save(user)
        if err:
            logger.error(
                "Failed to save user %s after updating transaction pin: %s",
                user_id,
                err.message,
                exc_info=True,
            )
            return None, err

        logger.info("Transaction pin for user %s updated successfully.", user_id)
        return updated_user, None

    async def verify_transaction_pin(
        self, user_id: UserId, pin: str
    ) -> Tuple[bool, Error]:
        logger.debug("Verifying transaction pin for user %s", user_id)
        user, err = await self.get_user_by_id(user_id)
        if err or not user:
            return False, err

        if not user.pin:
            logger.warning("Transaction pin not set for user %s", user_id)
            return False, None

        is_valid = verify_password(
            pin, HashedPassword(password_hash=user.pin.pin_hash), self.argon2_config
        )
        if is_valid:
            logger.info("Transaction pin verified successfully for user %s", user_id)
        else:
            logger.warning("Invalid transaction pin provided for user %s", user_id)
        return is_valid, None

    async def load_public_user(self, user_id: UserId) -> Tuple[Optional[dict], Error]:
        logger.debug("Loading public user data for user %s", user_id)
        user, err = await self.get_user_by_id(user_id)
        if err or not user:
            return None, err or NotFoundError

        user_data = user.model_dump()

        wallet = getattr(user, "wallet", None)
        wallets_data = []
        if wallet:
            source_wallets = wallet if isinstance(wallet, list) else [wallet]
            for w in source_wallets:
                w_dict = w.model_dump()
                assets_data = []
                if hasattr(w, "assets") and w.assets:
                    for a in w.assets:
                        a_dict = a.model_dump()
                        assets_data.append(a_dict)
                w_dict["assets"] = assets_data
                wallets_data.append(w_dict)

        user_data["wallets"] = wallets_data

        # Ensure profile is included in user_data and populated with necessary fields
        if hasattr(user, "profile") and user.profile:
            user_data["profile"] = user.profile.model_dump()

        try:
            public_user = UserPublic.model_validate(user_data)
            return public_user.model_dump(exclude_none=True), None
        except ValidationError as e:
            logger.error(
                "Failed to validate public user data for user %s: %s", user_id, str(e)
            )
            return None, error(f"Failed to load user data: {str(e)}")
