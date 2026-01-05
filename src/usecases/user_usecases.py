from typing import Optional, Tuple
from uuid import UUID

from src.dtos.user_dtos import UserCreate
from src.infrastructure.logger import get_logger
from src.infrastructure.repositories import UserRepository, WalletRepository
from src.infrastructure.services.blockrader_client import (AddressManager,
                                                           WalletManager)
from src.infrastructure.settings import BlockRaderConfig
from src.infrastructure.security import Argon2Config
from src.models import User, UserProfile, Wallet
from src.types import Error, HashedPassword, InvalidCredentialsError
from src.types.blockrader import CreateAddressRequest
from src.utils import hash_password_argon2, verify_password_argon2

logger = get_logger(__name__)


class UserUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        wallet_repository: WalletRepository,
        blockrader_config: BlockRaderConfig,
        argon2_config: Argon2Config,
    ):
        self.user_repository = user_repository
        self.wallet_repository = wallet_repository
        self.blockrader_config = blockrader_config
        self.argon2_config = argon2_config

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
        if not verify_password_argon2(password, hashed_password_obj, self.argon2_config):
            return None, InvalidCredentialsError
        return user, None

    async def save(self, user: User) -> Tuple[Optional[User], Error]:
        return await self.user_repository.save(user)

    async def update_user(
        self, user_id: UUID, /, **kwargs
    ) -> Tuple[Optional[User], Error]:
        return await self.user_repository.update_user(user_id=user_id, **kwargs)

    async def update_user_profile(
        self, user_id: UUID, /, **kwargs
    ) -> Tuple[Optional[UserProfile], Error]:
        return await self.user_repository.update_user_profile(user_id, **kwargs)

    async def create_user(
        self, user_create: UserCreate
    ) -> Tuple[Optional[User], Error]:
        hashed_password_obj = hash_password_argon2(user_create.password, self.argon2_config)
        user = User(
            email=user_create.email,
            password_hash=hashed_password_obj.password_hash,
            salt=hashed_password_obj.salt,
        )
        created_user, err = await self.user_repository.create_user(user=user)
        if err:
            logger.error(
                "Failed to create user in repository: %s", err.message, exc_info=True
            )
            return None, err
        logger.info(
            "User %s created successfully in repository.", created_user.username
        )

        wallet_manager = WalletManager(
            self.blockrader_config, self.blockrader_config.evm_master_wallet
        )
        create_address_req = CreateAddressRequest(
            name=f"{created_user.username}'s address",
            metadata={
                "user_id": str(created_user.id),
                "user_email": created_user.email,
            },
        )
        address_details, err = await wallet_manager.generate_address(create_address_req)
        address_manager = AddressManager(
            self.blockrader_config,
            self.blockrader_config.base_wallet_id,
            address_details.data.id,
        )

        if err:
            logger.error(
                "Failed to generate address for user %s: %s",
                created_user.username,
                err.message,
                exc_info=True,
            )
            await self.user_repository.delete_user(user_id=created_user.id)
            return None, err
        logger.info("Address generated for user %s.", created_user.username)

        address_balance_details, err = await address_manager.get_balance(
            self.blockrader_config.base_usdc_asset_id
        )

        if err:
            logger.error(
                "Failed to get address balance for user %s: %s",
                created_user.username,
                err.message,
                exc_info=True,
            )
            await self.user_repository.delete_user(user_id=created_user.id)
            return None, err
        logger.info("Address balance retrieved for user %s.", created_user.username)

        wallet = Wallet(
            user_id=created_user.id,
            address=address_details.data.address,
            provider_id=address_details.data.id,
            network=address_details.data.network,
            balance=address_balance_details.data.balance,
            usdc_asset_id=self.blockrader_config.base_usdc_asset_id,  # Added missing usdc_asset_id
        )

        _, err = await self.wallet_repository.create_wallet(wallet=wallet)
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

    async def get_user_by_id(self, user_id: UUID) -> Tuple[Optional[User], Error]:
        return await self.user_repository.get_user_by_id(user_id=user_id)

    async def get_user_by_email(self, user_email: str) -> Tuple[Optional[User], Error]:
        return await self.user_repository.get_user_by_email(email=user_email)


# TODO add on_delete  to user to delete proile and tied stuff
