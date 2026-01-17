from typing import Optional

from src.infrastructure.settings import BlockRaderConfig
from src.types import WebhookProvider
from src.infrastructure.logger import get_logger

logger = get_logger(__name__)


class SecretsUsecase:
    def __init__(self, blockrader_config: BlockRaderConfig) -> None:
        self.blockrader_config = blockrader_config
        logger.debug("SecretsUsecase initialized.")

    def get(self, provider: WebhookProvider) -> Optional[str]:
        logger.debug("Attempting to get secret for provider: %s", provider.value)
        if provider == WebhookProvider.BLOCKRADER:
            logger.debug("Returning BlockRader API key.")
            return self.blockrader_config.blockrader_api_key
        logger.debug("No secret found for provider: %s", provider.value)
        return None
