import logging
import httpx
from decimal import Decimal
from sqlalchemy.orm import Session

from ...models import User, Wallet
from ...config.blockradar import supported_wallets
from ....schemas.service_schema import GenerateAddressRequest, GenerateAddressResponse
from ...utils import get_wallet_type_from_blockchain
from ...settings import settings

logger = logging.getLogger("BlockradarService")


class BlockradarService:
    def __init__(self, db: Session):
        self.base_url = settings.blockradar_base_url.rstrip("/")
        self.db = db

    async def generate_address(
        self,
        user_id: int,
        blockchain_slug: str,
        request: GenerateAddressRequest,
    ) -> Wallet:
        # Get user details
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User not found: {user_id}")

        wallet_config = supported_wallets.get(blockchain_slug)
        if not wallet_config:
            raise ValueError(f"Unsupported blockchain: {blockchain_slug}")

        wallet_id = wallet_config.get("id")
        wallet_key = wallet_config.get("key")

        if not wallet_id or not wallet_key:
            raise ValueError(f"Missing wallet configuration for {blockchain_slug}")

        # Call Blockradar API
        url = f"{self.base_url}/wallets/{wallet_id}/addresses"
        headers = {
            "x-api-key": wallet_key,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, headers=headers, json=request.dict())

        if response.status_code != 200:
            logger.error(f"Blockradar API error: {response.text}")
            raise ValueError(f"Blockradar API error {response.status_code}")

        data = GenerateAddressResponse(**response.json())
        logger.info(f"Address generated successfully for user {user_id}")

        # Create wallet entity
        wallet = Wallet(
            user_id=user.id,
            address=data.data.address,
            type=get_wallet_type_from_blockchain(blockchain_slug),
        )
        self.db.add(wallet)
        self.db.commit()
        self.db.refresh(wallet)

        return wallet

    async def sweep_to_treasury(self, wallet: Wallet, amount: Decimal) -> str | None:
        """Sweep funds from user wallet to treasury wallet if auto-sweep is enabled"""
        wallet_config = supported_wallets.get(wallet.type)
        if not wallet_config:
            raise ValueError(f"Unsupported wallet type: {wallet.type}")

        if wallet_config.get("disableAutoSweep", False):
            logger.info(f"Auto-sweep disabled for wallet type: {wallet.type}")
            return None

        treasury_wallet_id = settings.treasury_wallet_id
        if not treasury_wallet_id:
            raise ValueError("Treasury wallet ID is not configured")

        url = f"{self.base_url}/wallets/{wallet_config['id']}/sweeps"
        headers = {
            "x-api-key": wallet_config["key"],
            "Content-Type": "application/json",
        }
        payload = {
            "fromAddress": wallet.address,
            "toWalletId": treasury_wallet_id,
            "amount": float(amount),
        }

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, headers=headers, json=payload)

        if response.status_code != 200:
            logger.error(f"Sweep API error: {response.text}")
            raise ValueError(f"Sweep API error {response.status_code}")

        sweep_data = response.json()
        tx_hash = sweep_data.get("txHash")
        logger.info(f"Sweep successful: {tx_hash}")

        return tx_hash
