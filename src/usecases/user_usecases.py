import uuid
from typing import Optional, Tuple

from src.dtos.user_dtos import UserCreate
from src.infrastructure.logger import get_logger
from src.infrastructure.repositories import UserRepository
from src.infrastructure.security import Argon2Config
from src.infrastructure.settings import BlockRaderConfig
from src.models import User, UserProfile
from src.types import Error, HashedPassword, InvalidCredentialsError
from src.types.common_types import UserId
from src.usecases.wallet_usecases import WalletManagerUsecase, WalletService
from src.utils import hash_password_argon2, verify_password_argon2

logger = get_logger(__name__)


class UserUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        blockrader_config: BlockRaderConfig,
        argon2_config: Argon2Config,
        wallet_manager_usecase: WalletManagerUsecase,
        wallet_service: WalletService,
    ):
        self.user_repository = user_repository
        self.blockrader_config = blockrader_config
        self.argon2_config = argon2_config
        self.wallet_manager_usecase = wallet_manager_usecase
        self.wallet_service = wallet_service
        logger.debug("UserUseCase initialized.")

    async def authenticate_user(
        self, email: str, password: str
    ) -> Tuple[Optional[User], Error]:
        logger.debug("Authenticating user with email: %s", email)
        user, err = await self.user_repository.get_user_by_email(email=email)
        if err:
            logger.debug("Error getting user by email %s: %s", email, err.message)
            return None, err
        if not user:
            logger.warning("Authentication failed: User with email %s not found.", email)
            return None, InvalidCredentialsError
        logger.debug("User %s found. Verifying password.", user.id)

        hashed_password_obj = HashedPassword(
            password_hash=user.password_hash, salt=user.salt
        )
        if not verify_password_argon2(
            password, hashed_password_obj, self.argon2_config
        ):
            logger.warning("Authentication failed: Invalid credentials for user %s", email)
            return None, InvalidCredentialsError
        logger.info("User %s authenticated successfully.", user.id)
        return user, None

    async def save(self, user: User) -> Tuple[Optional[User], Error]:
        logger.debug("Saving user with ID: %s", user.id)
        user, err = await self.user_repository.save(user)
        if err:
            logger.error("Failed to save user %s: %s", user.id, err.message)
        else:
            logger.info("User %s saved successfully.", user.id)
        return user, err

    async def update_user(
        self, user_id: UserId, /, **kwargs
    ) -> Tuple[Optional[User], Error]:
        logger.debug("Updating user %s with data: %s", user_id, kwargs)
        user, err = await self.user_repository.update_user(user_id=user_id, **kwargs)
        if err:
            logger.error("Failed to update user %s: %s", user_id, err.message)
        else:
            logger.info("User %s updated successfully.", user_id)
        return user, err

    async def update_user_profile(
        self, user_id: UserId, /, **kwargs
    ) -> Tuple[Optional[UserProfile], Error]:
        logger.debug("Updating user profile for user %s with data: %s", user_id, kwargs)
        user_profile, err = await self.user_repository.update_user_profile(user_id, **kwargs)
        if err:
            logger.error("Failed to update user profile for user %s: %s", user_id, err.message)
        else:
            logger.info("User profile for user %s updated successfully.", user_id)
        return user_profile, err

    async def create_user(
        self, user_create: UserCreate
    ) -> Tuple[Optional[User], Error]:
        logger.debug("Creating new user with email: %s", user_create.email)
        temp_ledger_identity_id = "temp_idty_%s" % uuid.uuid4()
        logger.debug("Generated temporary ledger identity ID: %s", temp_ledger_identity_id)

        hashed_password_obj = hash_password_argon2(
            user_create.password, self.argon2_config
        )
        user = User(
            email=user_create.email,
            password_hash=hashed_password_obj.password_hash,
            salt=hashed_password_obj.salt,
            first_name=user_create.first_name,
            last_name=user_create.last_name,
            gender=user_create.gender,
            ledger_identiy_id=temp_ledger_identity_id,
            username=user_create.username,
        )

        created_user, err = await self.user_repository.create_user(user=user)
        if err:
            logger.error(
                "Failed to create user in repository for email %s: %s", user_create.email, err.message, exc_info=True
            )
            return None, err
        logger.info(
            "User %s created successfully in repository with temporary ledger ID %s.",
            created_user.username, temp_ledger_identity_id
        )

        logger.debug("Creating ledger identity for user %s", created_user.username)
        ledger_identity, err = await self.wallet_service.create_ledger_identity(
            created_user # Changed from user_create to created_user to pass the User object
        )
        if err:
            logger.error(
                "Failed to create ledger identity for user %s: %s",
                created_user.username,
                err.message,
                exc_info=True,
            )
            rollback_err = await self.user_repository.rollback()
            if rollback_err:
                logger.error(
                    "Failed to rollback user creation for user %s after ledger identity failure: %s",
                    created_user.username,
                    rollback_err.message,
                    exc_info=True,
                )
            return None, err
        logger.info("Ledger identity %s created for user %s.", ledger_identity.identity_id, created_user.username)

        logger.debug("Updating user %s with real ledger ID: %s", created_user.username, ledger_identity.identity_id)
        created_user, err = await self.user_repository.update_user(
            user_id=created_user.id, ledger_identiy_id=ledger_identity.identity_id
        )
        if err:
            logger.error(
                "Failed to update user %s with real ledger ID %s: %s",
                created_user.username, ledger_identity.identity_id,
                err.message,
                exc_info=True,
            )
            return None, err
        logger.info("User %s updated with real ledger ID %s.", created_user.username, ledger_identity.identity_id)

        logger.debug("Creating wallet for user %s", created_user.username)
        _, err = await self.wallet_manager_usecase.create_user_wallet(created_user.id)
        if err:
            logger.error(
                "Failed to create wallet for user %s: %s",
                created_user.username,
                err.message,
                exc_info=True,
            )
            return None, err
        logger.info("Wallet created for user %s.", created_user.username)

        logger.info(
            "User %s and associated wallet created successfully.", created_user.username
        )
        return created_user, None

    async def get_user_by_id(self, user_id: UserId) -> Tuple[Optional[User], Error]:
        logger.debug("Getting user by ID: %s", user_id)
        user, err = await self.user_repository.get_user_by_id(user_id=user_id)
        if err:
            logger.debug("User %s not found: %s", user_id, err.message)
        else:
            logger.debug("User %s retrieved.", user_id)
        return user, err

    async def get_user_by_email(self, user_email: str) -> Tuple[Optional[User], Error]:
        logger.debug("Getting user by email: %s", user_email)
        user, err = await self.user_repository.get_user_by_email(email=user_email)
        if err:
            logger.debug("User with email %s not found: %s", user_email, err.message)
        else:
            logger.debug("User with email %s retrieved.", user_email)
        return user, err
