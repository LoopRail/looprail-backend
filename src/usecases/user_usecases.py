from typing import Optional, Tuple
from uuid import UUID

from src.dtos.user_dtos import UserCreate
from src.infrastructure.logger import get_logger
from src.infrastructure.services.blockrader_client import (AddressManager,
                                                           WalletManager)
from src.infrastructure.settings import BlockRaderConfig
from src.models.user_model import User, UserRepository
from src.models.wallet_model import Wallet, WalletRepository
from src.types.blockrader_types import CreateAddressRequest
from src.types.error import Error

logger = get_logger(__name__)


class UserUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        wallet_repository: WalletRepository,
        blockrader_config: BlockRaderConfig,
    ):
        self.user_repository = user_repository
        self.wallet_repository = wallet_repository
        self.blockrader_config = blockrader_config

    async def create_user(
        self, user_create: UserCreate
    ) -> Tuple[Optional[User], Error]:
        user = User(
            first_name=user_create.first_name,
            last_name=user_create.last_name,
            email=user_create.email,
            username=user_create.username,
        )
        created_user, err = await self.user_repository.create_user(user=user)
        if err:
            logger.error("Failed to create user in repository: %s", err.message, exc_info=True)
            return None, err
        logger.info("User %s created successfully in repository.", created_user.username)

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
                "Failed to generate address for user %s: %s", created_user.username, err.message, exc_info=True
            )
            await self.user_repository.delete_user(user_id=created_user.id)
            return None, err
        logger.info("Address generated for user %s.", created_user.username)

        address_balance_details, err = await address_manager.get_balance(
            self.blockrader_config.base_usdc_asset_id
        )

        if err:
            logger.error(
                "Failed to get address balance for user %s: %s", created_user.username, err.message, exc_info=True
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
                "Failed to create wallet for user %s: %s", created_user.username, err.message, exc_info=True
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
