from typing import Any, Optional, Tuple, Type

from httpx import Response

from src.infrastructure.services.base_client import BaseClient, T
from src.infrastructure.settings import LedgderServiceConfig
from src.types import Error, httpError
from src.types.blnk.dtos import (
    BalanceMonitorResponse,
    BalanceResponse,
    BlnkBase,
    CreateBalanceMonitorRequest,
    CreateBalanceRequest,
    CreateIdentityRequest,
    CreateLedgerRequest,
    CreateReconMatchingRulesRequest,
    IdentityResponse,
    LedgerResponse,
    PostMetadataRequest,
    RecordBulkTransactionRequest,
    RecordTransactionRequest,
    ReconciliationUploadRequest,
    RefundTransactionResponse,
    SearchTransactionRequest,
    StartInstantReconciliationRequest,
    StartReconciliationRequest,
    TokenizeFieldsRequest,
    TransactionResponse,
    UpdateBalanceMonitorRequest,
    UpdateInflightTransactionRequest,
)
from src.infrastructure.logger import get_logger

logger = get_logger(__name__)


class BlnkClient(BaseClient):
    """A base client for interacting with the Blnk API."""

    def __init__(self, config: LedgderServiceConfig, path: str) -> None:
        """Initializes the Blnk client.

        Args:
            config: The LedgderServiceConfig configuration.
            path: The base path for the API endpoints.
        """
        self.config = config
        super().__init__(path)
        logger.debug("BlnkClient initialized with path: %s", path)

    def _get_base_url(self) -> str:
        logger.debug("Getting Blnk base URL: %s", self.config.ledger_service_host)
        return self.config.ledger_service_host

    def _get_headers(self) -> dict[str, str]:
        logger.debug("Getting Blnk headers with API key.")
        return {"X-Blnk-Key": self.config.ledger_service_api_key}

    def _process_response(
        self, res: Response, response_model: Type[T]
    ) -> Tuple[Optional[T], Error]:
        """Processes the HTTP response from the Blnk API."""
        logger.debug(
            "Processing Blnk response for URL: %s with status code: %s",
            res.url,
            res.status_code,
        )
        if not res.is_success:
            logger.error(
                "Blnk API request failed (status code: %s): %s for request to %s",
                res.status_code,
                res.json(),
                res.url,
            )
            return None, httpError(
                code=res.status_code,
                message=f"Blnk API request failed {res.status_code}: {res.json()}",
            )

        response_data = response_model.model_validate(res.json())
        logger.debug("Blnk response validated with model %s", response_model.__name__)
        return response_data, None


class LedgerManager(BlnkClient):
    """Manages ledger-related operations."""

    def __init__(self, config: LedgderServiceConfig) -> None:
        super().__init__(config, path="/ledgers")
        logger.debug("LedgerManager initialized.")

    async def create_ledger(
        self, request: CreateLedgerRequest
    ) -> Tuple[Optional[LedgerResponse], Error]:
        logger.debug(
            "Creating ledger with request: %s", request.model_dump(by_alias=True)
        )
        return await self._post(
            LedgerResponse,
            data=request.model_dump(by_alias=True),
        )

    async def get_ledger(
        self, ledger_id: str
    ) -> Tuple[Optional[LedgerResponse], Error]:
        logger.debug("Getting ledger with ID: %s", ledger_id)
        return await self._get(
            LedgerResponse,
            path_suffix=f"/{ledger_id}",
        )


class BalanceManager(BlnkClient):
    """Manages balance-related operations."""

    def __init__(self, config: LedgderServiceConfig) -> None:
        super().__init__(config, path="/balances")
        logger.debug("BalanceManager initialized.")

    async def create_balance(
        self, request: CreateBalanceRequest
    ) -> Tuple[Optional[BalanceResponse], Error]:
        logger.debug(
            "Creating balance with request: %s", request.model_dump(by_alias=True)
        )
        return await self._post(
            BalanceResponse,
            data=request.model_dump(by_alias=True),
        )

    async def get_balance(
        self, balance_id: str
    ) -> Tuple[Optional[BalanceResponse], Error]:
        logger.debug("Getting balance with ID: %s", balance_id)
        return await self._get(
            BalanceResponse,
            path_suffix=f"/{balance_id}",
        )

    async def take_balance_snapshots(self) -> Tuple[Any, Error]:
        """Placeholder for Take Balance snapshots endpoint.
        The Postman collection does not provide a response DTO for this."""
        logger.debug("Taking balance snapshots.")
        return await self._post(
            BlnkBase,  # Using BlnkBase as a placeholder for response
            path_suffix="/snapshots",
        )


class IdentityManager(BlnkClient):
    """Manages identity-related operations."""

    def __init__(self, config: LedgderServiceConfig) -> None:
        super().__init__(config, path="/identities")
        logger.debug("IdentityManager initialized.")

    async def create_identity(
        self, request: CreateIdentityRequest
    ) -> Tuple[Optional[IdentityResponse], Error]:
        logger.debug(
            "Creating identity with request: %s", request.model_dump(by_alias=True)
        )
        return await self._post(
            IdentityResponse,
            data=request.model_dump(by_alias=True),
        )

    async def get_identity(
        self, identity_id: str
    ) -> Tuple[Optional[IdentityResponse], Error]:
        logger.debug("Getting identity with ID: %s", identity_id)
        return await self._get(
            IdentityResponse,
            path_suffix=f"/{identity_id}",
        )

    async def get_tokenized_fields(self, identity_id: str) -> Tuple[Any, Error]:
        """Placeholder for Get Tokenized Fields endpoint."""
        logger.debug("Getting tokenized fields for identity ID: %s", identity_id)
        return await self._get(
            BlnkBase,  # Placeholder
            path_suffix=f"/{identity_id}/tokenized-fields",
        )

    async def tokenize_field(self, identity_id: str, field: str) -> Tuple[Any, Error]:
        """Placeholder for Tokenized Field endpoint."""
        logger.debug("Tokenizing field %s for identity ID: %s", field, identity_id)
        return await self._post(
            BlnkBase,  # Placeholder
            path_suffix=f"/{identity_id}/tokenize/{field}",
        )

    async def detokenize_field(self, identity_id: str, field: str) -> Tuple[Any, Error]:
        """Placeholder for Detokenize Field endpoint."""
        logger.debug("Detokenizing field %s for identity ID: %s", field, identity_id)
        return await self._get(
            BlnkBase,  # Placeholder
            path_suffix=f"/{identity_id}/detokenize/{field}",
        )

    async def tokenize_identity(
        self, identity_id: str, request: TokenizeFieldsRequest
    ) -> Tuple[Any, Error]:
        """Placeholder for tokenize Identity endpoint."""
        logger.debug(
            "Tokenizing identity %s with request: %s",
            identity_id,
            request.model_dump(by_alias=True),
        )
        return await self._post(
            BlnkBase,  # Placeholder
            path_suffix=f"/{identity_id}/tokenize",
            data=request.model_dump(by_alias=True),
        )

    async def detokenize_identity(
        self, identity_id: str, request: TokenizeFieldsRequest
    ) -> Tuple[Any, Error]:
        """Placeholder for Detokenize Identity endpoint."""
        logger.debug(
            "Detokenizing identity %s with request: %s",
            identity_id,
            request.model_dump(by_alias=True),
        )
        return await self._post(
            BlnkBase,  # Placeholder
            path_suffix=f"/{identity_id}/detokenize",
            data=request.model_dump(by_alias=True),
        )


class TransactionManager(BlnkClient):
    """Manages transaction-related operations."""

    def __init__(self, config: LedgderServiceConfig) -> None:
        super().__init__(config, path="/transactions")
        logger.debug("TransactionManager initialized.")

    async def record_transaction(
        self, request: RecordTransactionRequest
    ) -> Tuple[Optional[TransactionResponse], Error]:
        logger.debug(
            "Recording transaction with request: %s", request.model_dump(by_alias=True)
        )
        return await self._post(
            TransactionResponse,
            data=request.model_dump(by_alias=True),
        )

    async def record_bulk_transaction(
        self, request: RecordBulkTransactionRequest
    ) -> Tuple[Any, Error]:
        """Placeholder for Record Bulk Transaction endpoint."""
        logger.debug(
            "Recording bulk transaction with request: %s",
            request.model_dump(by_alias=True),
        )
        return await self._post(
            BlnkBase,  # Placeholder
            path_suffix="/bulk",
            data=request.model_dump(by_alias=True),
        )

    async def refund_transaction(
        self, transaction_id: str
    ) -> Tuple[Optional[RefundTransactionResponse], Error]:
        logger.debug("Refunding transaction with ID: %s", transaction_id)
        return await self._post(
            RefundTransactionResponse,
            path_suffix=f"/refund-transaction/{transaction_id}",  # This path is unusual
        )

    async def update_inflight_transaction(
        self, transaction_id: str, request: UpdateInflightTransactionRequest
    ) -> Tuple[Any, Error]:
        """Placeholder for Update Inflight Transaction endpoint."""
        logger.debug(
            "Updating inflight transaction %s with request: %s",
            transaction_id,
            request.model_dump(by_alias=True),
        )
        return await self._put(
            BlnkBase,
            path_suffix=f"/inflight/{transaction_id}",
            data=request.model_dump(by_alias=True),
        )

    async def search_transactions(
        self, request: SearchTransactionRequest
    ) -> Tuple[Any, Error]:
        """Placeholder for Search Transactions endpoint."""
        logger.debug(
            "Searching transactions with request: %s", request.model_dump(by_alias=True)
        )
        return await self._post(  # Assuming POST method based on Postman
            BlnkBase,  # Placeholder
            path_suffix="/search/transactions",
            data=request.model_dump(by_alias=True),
        )


class BalanceMonitorManager(BlnkClient):
    """Manages balance monitor-related operations."""

    def __init__(self, config: LedgderServiceConfig) -> None:
        super().__init__(config, path="/balance-monitors")
        logger.debug("BalanceMonitorManager initialized.")

    async def create_balance_monitor(
        self, request: CreateBalanceMonitorRequest
    ) -> Tuple[Optional[BalanceMonitorResponse], Error]:
        logger.debug(
            "Creating balance monitor with request: %s",
            request.model_dump(by_alias=True),
        )
        return await self._post(
            BalanceMonitorResponse,
            data=request.model_dump(by_alias=True),
        )

    async def update_balance_monitor(
        self, monitor_id: str, request: UpdateBalanceMonitorRequest
    ) -> Tuple[Any, Error]:
        """Placeholder for Update Balance Monitor endpoint."""
        logger.debug(
            "Updating balance monitor %s with request: %s",
            monitor_id,
            request.model_dump(by_alias=True),
        )
        return await self._put(  # Assuming PUT method based on Postman
            BlnkBase,  # Placeholder
            path_suffix=f"/{monitor_id}",
            data=request.model_dump(by_alias=True),
        )

    async def get_balance_monitor(
        self, monitor_id: str
    ) -> Tuple[Optional[BalanceMonitorResponse], Error]:
        logger.debug("Getting balance monitor with ID: %s", monitor_id)
        return await self._get(
            BalanceMonitorResponse,
            path_suffix=f"/{monitor_id}",
        )


class ReconciliationManager(BlnkClient):
    """Manages reconciliation-related operations."""

    def __init__(self, config: LedgderServiceConfig) -> None:
        super().__init__(config, path="/reconciliation")
        logger.debug("ReconciliationManager initialized.")

    async def upload_reconciliation_file(
        self, request: ReconciliationUploadRequest
    ) -> Tuple[Any, Error]:
        """Placeholder for Reconciliation Upload endpoint."""
        logger.debug(
            "Uploading reconciliation file with request: %s",
            request.model_dump(by_alias=True),
        )
        # This will require handling file uploads, potentially different from data=json
        return await self._post(
            BlnkBase,  # Placeholder
            path_suffix="/upload",
            data=request.model_dump(
                by_alias=True
            ),  # This might not be suitable for file upload
        )

    async def create_matching_rules(
        self, request: CreateReconMatchingRulesRequest
    ) -> Tuple[Any, Error]:
        """Placeholder for Create Recon Matching Rules endpoint."""
        logger.debug(
            "Creating matching rules with request: %s",
            request.model_dump(by_alias=True),
        )
        return await self._post(
            BlnkBase,  # Placeholder
            path_suffix="/matching-rules",
            data=request.model_dump(by_alias=True),
        )

    async def start_reconciliation(
        self, request: StartReconciliationRequest
    ) -> Tuple[Any, Error]:
        """Placeholder for Start Reconciliation endpoint."""
        logger.debug(
            "Starting reconciliation with request: %s",
            request.model_dump(by_alias=True),
        )
        return await self._post(
            BlnkBase,  # Placeholder
            path_suffix="/start",
            data=request.model_dump(by_alias=True),
        )

    async def start_instant_reconciliation(
        self, request: StartInstantReconciliationRequest
    ) -> Tuple[Any, Error]:
        """Placeholder for Start Instant Reconciliation endpoint."""
        logger.debug(
            "Starting instant reconciliation with request: %s",
            request.model_dump(by_alias=True),
        )
        return await self._post(
            BlnkBase,  # Placeholder
            path_suffix="/start-instant",
            data=request.model_dump(by_alias=True),
        )

    async def get_reconciliation(self, reconciliation_id: str) -> Tuple[Any, Error]:
        """Placeholder for Get Reconciliation endpoint."""
        logger.debug("Getting reconciliation with ID: %s", reconciliation_id)
        return await self._get(
            BlnkBase,  # Placeholder
            path_suffix=f"/{reconciliation_id}",
        )


class BlnkHookManager(BlnkClient):
    """Manages Blnk webhook operations."""

    def __init__(self, config: LedgderServiceConfig) -> None:
        super().__init__(config, path="/hooks")
        logger.debug("BlnkHookManager initialized.")

    async def register_hook(self) -> Tuple[Any, Error]:
        """Placeholder for Register Hook endpoint.
        The Postman collection request body suggests a POST, but the method is GET.
        Also, the URL in Postman is 'hoo', which is likely incorrect."""
        logger.debug("Registering hook.")
        return await self._post(  # Assuming POST based on body presence
            BlnkBase,  # Placeholder
            # No specific data/response model provided in Postman for successful registration
        )


class BlnkApiKeyManager(BlnkClient):
    """Manages Blnk API Key operations."""

    def __init__(self, config: LedgderServiceConfig) -> None:
        super().__init__(config, path="/api-keys")
        logger.debug("BlnkApiKeyManager initialized.")

    async def generate_api_key(self) -> Tuple[Any, Error]:
        """Placeholder for Generate API Key endpoint."""
        logger.debug("Generating API key.")
        return await self._post(
            BlnkBase,  # Placeholder
        )


class BlnkGenericManager(BlnkClient):
    """Manages generic Blnk operations like metadata updates."""

    def __init__(self, config: LedgderServiceConfig) -> None:
        super().__init__(config, path="")  # Path is dynamic for /:id/metadata
        logger.debug("BlnkGenericManager initialized.")

    async def post_metadata(
        self, entity_id: str, request: PostMetadataRequest
    ) -> Tuple[Any, Error]:
        """Placeholder for Post MetaData endpoint."""
        logger.debug(
            "Posting metadata for entity %s with request: %s",
            entity_id,
            request.model_dump(by_alias=True),
        )
        return await self._post(
            BlnkBase,  # Placeholder
            path_suffix=f"/{entity_id}/metadata",
            data=request.model_dump(by_alias=True),
        )
