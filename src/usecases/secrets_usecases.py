from typing import Optional

from src.infrastructure.logger import get_logger
from src.infrastructure.settings import BlockRaderConfig, PayCrestConfig
from src.types import WebhookProvider

logger = get_logger(__name__)


class SecretsUsecase:
    def __init__(
        self, blockrader_config: BlockRaderConfig, paycrest_config: PayCrestConfig
    ):
        self.blockrader_config = blockrader_config
        self.paycrest_config = paycrest_config
        logger.debug("SecretsUsecase initialized.")

    def get(self, provider: WebhookProvider) -> Optional[str]:
        logger.debug("Attempting to get secret for provider: %s", provider.value)
        if provider == WebhookProvider.BLOCKRADER:
            logger.debug("Returning BlockRader API key.")
            return self.blockrader_config.blockrader_api_key
        if provider == WebhookProvider.PAYCREST:
            logger.debug("Returning PayCrest API key.")
            return self.paycrest_config.paycrest_api_secret
        logger.debug("No secret found for provider: %s", provider.value)
        return None
