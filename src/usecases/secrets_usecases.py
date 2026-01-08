from typing import Optional

from src.infrastructure.settings import BlockRaderConfig
from src.types import WebhookProvider


class SecretsUsecase:
    def __init__(self, blockrader_config: BlockRaderConfig) -> None:
        self.blockrader_config = blockrader_config

    def get(self, provider: WebhookProvider) -> Optional[str]:
        if provider == WebhookProvider.BLOCKRADER:
            return self.blockrader_config.blockrader_api_key
        return None
