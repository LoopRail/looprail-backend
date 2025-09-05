from ..settings import settings

supported_wallets = {
    "ethereum": {"id": settings.blockradar_ethereum_wallet_id, "key": settings.blockradar_ethereum_wallet_api_key},
}

default_wallet = supported_wallets["ethereum"]