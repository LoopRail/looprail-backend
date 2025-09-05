from typing import Optional, Tuple
from uuid import UUID

from src.dtos.user_dtos import UserCreate
from src.infrastructure.services.blockrader_client import (AddressManager,
                                                           WalletManager)
from src.infrastructure.settings import BlockRaderConfig
from src.models.user_model import User, UserRepository
from src.models.wallet_model import Wallet, WalletRepository
from src.types.blockrader_types import CreateAddressRequest
from src.types.error import Error
from src.infrastructure.logger import get_logger

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
            return None, err

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
            self.blockrader_config, address_details.data.id
        )

        if err:
            await self.user_repository.delete_user(user_id=created_user.id)
            return None, err

        address_balance_details, err = await address_manager.get_balance(
            self.blockrader_config.base_usdc_asset_id
        )

        if err:
            await self.user_repository.delete_user(user_id=created_user.id)
            return None, err

        wallet = Wallet(
            user_id=created_user.id,
            address=address_details.data.address,
            provider_id=address_details.data.id,
            network=address_details.data.network,
            balance=address_balance_details.data.balance,
        )

        _, err = await self.wallet_repository.create_wallet(wallet=wallet)
        if err:
            await self.user_repository.delete_user(user_id=created_user.id)
            return None, err

        return created_user, None

    async def get_user_by_id(self, user_id: UUID) -> Tuple[Optional[User], Error]:
        return await self.user_repository.get_user_by_id(user_id=user_id)
