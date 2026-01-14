import uuid
from typing import Optional, Tuple

from src.dtos.user_dtos import UserCreate
from src.infrastructure.logger import get_logger
from src.infrastructure.repositories import UserRepository, WalletRepository
from src.infrastructure.security import Argon2Config
from src.infrastructure.services.blockrader_client import AddressManager, WalletManager
from src.infrastructure.settings import BlockRaderConfig
from src.models import User, UserProfile, Wallet
from src.types import Error, HashedPassword, InvalidCredentialsError
from src.types.blockrader import CreateAddressRequest
from src.types.common_types import UserId
from src.usecases.wallet_usecases import WalletManagerUsecase  # Added
from src.usecases.wallet_usecases import WalletService
from src.utils import hash_password_argon2, verify_password_argon2

logger = get_logger(__name__)


class UserUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        wallet_repository: WalletRepository,
        blockrader_config: BlockRaderConfig,
        argon2_config: Argon2Config,
        wallet_manager_usecase: WalletManagerUsecase,  # Added this line
        wallet_service: WalletService,  # Added this line
    ):
        self.user_repository = user_repository
        self.wallet_repository = wallet_repository
        self.blockrader_config = blockrader_config
        self.argon2_config = argon2_config
        self.wallet_manager_usecase = wallet_manager_usecase  # Added this line
        self.wallet_service = wallet_service  # Added this line

    async def authenticate_user(
        self, email: str, password: str
    ) -> Tuple[Optional[User], Error]:
        user, err = await self.user_repository.get_user_by_email(email=email)
        if err:
            return None, err
        if not user:
            return None, InvalidCredentialsError

        hashed_password_obj = HashedPassword(
            password_hash=user.password_hash, salt=user.salt
        )
        if not verify_password_argon2(
            password, hashed_password_obj, self.argon2_config
        ):
            return None, InvalidCredentialsError
        return user, None

    async def save(self, user: User) -> Tuple[Optional[User], Error]:
        return await self.user_repository.save(user)

    async def update_user(
        self, user_id: UserId, /, **kwargs
    ) -> Tuple[Optional[User], Error]:
        return await self.user_repository.update_user(user_id=user_id, **kwargs)

    async def update_user_profile(
        self, user_id: UserId, /, **kwargs
    ) -> Tuple[Optional[UserProfile], Error]:
        return await self.user_repository.update_user_profile(user_id, **kwargs)

    async def create_user(
        self, user_create: UserCreate
    ) -> Tuple[Optional[User], Error]:
        temp_ledger_identity_id = f"temp_idty_{uuid.uuid4()}"

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
                "Failed to create user in repository: %s", err.message, exc_info=True
            )
            return None, err
        logger.info(
            "User %s created successfully in repository with temporary ledger ID.",
            created_user.username,
        )

        ledger_identity, err = await self.wallet_service.create_ledger_identity(
            user_create
        )
        if err:
            logger.error(
                "Failed to create ledger identity for user %s: %s",
                created_user.username,
                err.message,
                exc_info=True,
            )
            await self.user_repository.delete_user(user_id=created_user.id)
            return None, err
        logger.info("Ledger identity created for user %s.", created_user.username)

        created_user, err = await self.user_repository.update_user(
            user_id=created_user.id, ledger_identiy_id=ledger_identity.identity_id
        )
        if err:
            logger.error(
                "Failed to update user with real ledger ID for user %s: %s",
                created_user.username,
                err.message,
                exc_info=True,
            )
            await self.user_repository.delete_user(user_id=created_user.id)
            return None, err

        _, err = await self.wallet_manager_usecase.create_user_wallet(created_user.id)
        if err:
            logger.error(
                "Failed to create wallet for user %s: %s",
                created_user.username,
                err.message,
                exc_info=True,
            )
            await self.user_repository.delete_user(user_id=created_user.id)
            return None, err
        logger.info("Wallet created for user %s.", created_user.username)

        logger.info(
            "User %s and associated wallet created successfully.", created_user.username
        )
        return created_user, None

    async def get_user_by_id(self, user_id: UserId) -> Tuple[Optional[User], Error]:
        return await self.user_repository.get_user_by_id(user_id=user_id)

    async def get_user_by_email(self, user_email: str) -> Tuple[Optional[User], Error]:
        return await self.user_repository.get_user_by_email(email=user_email)


# TODO add on_delete  to user to delete proile and tied stuff
