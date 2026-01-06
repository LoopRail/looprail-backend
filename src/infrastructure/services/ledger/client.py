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

    def _get_base_url(self) -> str:
        return self.config.ledger_service_host

    def _get_headers(self) -> dict[str, str]:
        return {"X-Blnk-Key": self.config.ledger_service_api_key}

    def _process_response(
        self, res: Response, response_model: Type[T]
    ) -> Tuple[Optional[T], Error]:
        """Processes the HTTP response from the Blnk API."""
        if not res.is_success:
            return None, httpError(
                code=res.status_code,
                message=f"Blnk API request failed {res.status_code}: {res.json()}",
            )

        return response_model.model_validate(res.json()), None


class LedgerManager(BlnkClient):
    """Manages ledger-related operations."""

    def __init__(self, config: LedgderServiceConfig) -> None:
        super().__init__(config, path="/ledgers")

    async def create_ledger(
        self, request: CreateLedgerRequest
    ) -> Tuple[Optional[LedgerResponse], Error]:
        return await self._post(
            LedgerResponse,
            data=request.model_dump(by_alias=True),
        )

    async def get_ledger(
        self, ledger_id: str
    ) -> Tuple[Optional[LedgerResponse], Error]:
        return await self._get(
            LedgerResponse,
            path_suffix=f"/{ledger_id}",
        )


class BalanceManager(BlnkClient):
    """Manages balance-related operations."""

    def __init__(self, config: LedgderServiceConfig) -> None:
        super().__init__(config, path="/balances")

    async def create_balance(
        self, request: CreateBalanceRequest
    ) -> Tuple[Optional[BalanceResponse], Error]:
        return await self._post(
            BalanceResponse,
            data=request.model_dump(by_alias=True),
        )

    async def get_balance(
        self, balance_id: str
    ) -> Tuple[Optional[BalanceResponse], Error]:
        return await self._get(
            BalanceResponse,
            path_suffix=f"/{balance_id}",
        )

    async def take_balance_snapshots(self) -> Tuple[Any, Error]:
        """Placeholder for Take Balance snapshots endpoint.
        The Postman collection does not provide a response DTO for this."""
        return await self._post(
            BlnkBase,  # Using BlnkBase as a placeholder for response
            path_suffix="/snapshots",
        )


class IdentityManager(BlnkClient):
    """Manages identity-related operations."""

    def __init__(self, config: LedgderServiceConfig) -> None:
        super().__init__(config, path="/identities")

    async def create_identity(
        self, request: CreateIdentityRequest
    ) -> Tuple[Optional[IdentityResponse], Error]:
        return await self._post(
            IdentityResponse,
            data=request.model_dump(by_alias=True),
        )

    async def get_identity(
        self, identity_id: str
    ) -> Tuple[Optional[IdentityResponse], Error]:
        return await self._get(
            IdentityResponse,
            path_suffix=f"/{identity_id}",
        )

    async def get_tokenized_fields(self, identity_id: str) -> Tuple[Any, Error]:
        """Placeholder for Get Tokenized Fields endpoint."""
        return await self._get(
            BlnkBase,  # Placeholder
            path_suffix=f"/{identity_id}/tokenized-fields",
        )

    async def tokenize_field(self, identity_id: str, field: str) -> Tuple[Any, Error]:
        """Placeholder for Tokenized Field endpoint."""
        return await self._post(
            BlnkBase,  # Placeholder
            path_suffix=f"/{identity_id}/tokenize/{field}",
        )

    async def detokenize_field(self, identity_id: str, field: str) -> Tuple[Any, Error]:
        """Placeholder for Detokenize Field endpoint."""
        return await self._get(
            BlnkBase,  # Placeholder
            path_suffix=f"/{identity_id}/detokenize/{field}",
        )

    async def tokenize_identity(
        self, identity_id: str, request: TokenizeFieldsRequest
    ) -> Tuple[Any, Error]:
        """Placeholder for tokenize Identity endpoint."""
        return await self._post(
            BlnkBase,  # Placeholder
            path_suffix=f"/{identity_id}/tokenize",
            data=request.model_dump(by_alias=True),
        )

    async def detokenize_identity(
        self, identity_id: str, request: TokenizeFieldsRequest
    ) -> Tuple[Any, Error]:
        """Placeholder for Detokenize Identity endpoint."""
        return await self._post(
            BlnkBase,  # Placeholder
            path_suffix=f"/{identity_id}/detokenize",
            data=request.model_dump(by_alias=True),
        )


class TransactionManager(BlnkClient):
    """Manages transaction-related operations."""

    def __init__(self, config: LedgderServiceConfig) -> None:
        super().__init__(config, path="/transactions")

    async def record_transaction(
        self, request: RecordTransactionRequest
    ) -> Tuple[Optional[TransactionResponse], Error]:
        return await self._post(
            TransactionResponse,
            data=request.model_dump(by_alias=True),
        )

    async def record_bulk_transaction(
        self, request: RecordBulkTransactionRequest
    ) -> Tuple[Any, Error]:
        """Placeholder for Record Bulk Transaction endpoint."""
        return await self._post(
            BlnkBase,  # Placeholder
            path_suffix="/bulk",
            data=request.model_dump(by_alias=True),
        )

    async def refund_transaction(
        self, transaction_id: str
    ) -> Tuple[Optional[RefundTransactionResponse], Error]:
        return await self._post(
            RefundTransactionResponse,
            path_suffix=f"/refund-transaction/{transaction_id}",  # This path is unusual
        )

    async def update_inflight_transaction(
        self, transaction_id: str, request: UpdateInflightTransactionRequest
    ) -> Tuple[Any, Error]:
        """Placeholder for Update Inflight Transaction endpoint."""
        return await self._put(  # Assuming PUT method based on Postman
            BlnkBase,  # Placeholder
            path_suffix=f"/inflight/{transaction_id}",
            data=request.model_dump(by_alias=True),
        )

    async def search_transactions(
        self, request: SearchTransactionRequest
    ) -> Tuple[Any, Error]:
        """Placeholder for Search Transactions endpoint."""
        return await self._post(  # Assuming POST method based on Postman
            BlnkBase,  # Placeholder
            path_suffix="/search/transactions",
            data=request.model_dump(by_alias=True),
        )


class BalanceMonitorManager(BlnkClient):
    """Manages balance monitor-related operations."""

    def __init__(self, config: LedgderServiceConfig) -> None:
        super().__init__(config, path="/balance-monitors")

    async def create_balance_monitor(
        self, request: CreateBalanceMonitorRequest
    ) -> Tuple[Optional[BalanceMonitorResponse], Error]:
        return await self._post(
            BalanceMonitorResponse,
            data=request.model_dump(by_alias=True),
        )

    async def update_balance_monitor(
        self, monitor_id: str, request: UpdateBalanceMonitorRequest
    ) -> Tuple[Any, Error]:
        """Placeholder for Update Balance Monitor endpoint."""
        return await self._put(  # Assuming PUT method based on Postman
            BlnkBase,  # Placeholder
            path_suffix=f"/{monitor_id}",
            data=request.model_dump(by_alias=True),
        )

    async def get_balance_monitor(
        self, monitor_id: str
    ) -> Tuple[Optional[BalanceMonitorResponse], Error]:
        return await self._get(
            BalanceMonitorResponse,
            path_suffix=f"/{monitor_id}",
        )


class ReconciliationManager(BlnkClient):
    """Manages reconciliation-related operations."""

    def __init__(self, config: LedgderServiceConfig) -> None:
        super().__init__(config, path="/reconciliation")

    async def upload_reconciliation_file(
        self, request: ReconciliationUploadRequest
    ) -> Tuple[Any, Error]:
        """Placeholder for Reconciliation Upload endpoint."""
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
        return await self._post(
            BlnkBase,  # Placeholder
            path_suffix="/matching-rules",
            data=request.model_dump(by_alias=True),
        )

    async def start_reconciliation(
        self, request: StartReconciliationRequest
    ) -> Tuple[Any, Error]:
        """Placeholder for Start Reconciliation endpoint."""
        return await self._post(
            BlnkBase,  # Placeholder
            path_suffix="/start",
            data=request.model_dump(by_alias=True),
        )

    async def start_instant_reconciliation(
        self, request: StartInstantReconciliationRequest
    ) -> Tuple[Any, Error]:
        """Placeholder for Start Instant Reconciliation endpoint."""
        return await self._post(
            BlnkBase,  # Placeholder
            path_suffix="/start-instant",
            data=request.model_dump(by_alias=True),
        )

    async def get_reconciliation(self, reconciliation_id: str) -> Tuple[Any, Error]:
        """Placeholder for Get Reconciliation endpoint."""
        return await self._get(
            BlnkBase,  # Placeholder
            path_suffix=f"/{reconciliation_id}",
        )


class BlnkHookManager(BlnkClient):
    """Manages Blnk webhook operations."""

    def __init__(self, config: LedgderServiceConfig) -> None:
        super().__init__(config, path="/hooks")

    async def register_hook(self) -> Tuple[Any, Error]:
        """Placeholder for Register Hook endpoint.
        The Postman collection request body suggests a POST, but the method is GET.
        Also, the URL in Postman is 'hoo', which is likely incorrect."""
        return await self._post(  # Assuming POST based on body presence
            BlnkBase,  # Placeholder
            # No specific data/response model provided in Postman for successful registration
        )


class BlnkApiKeyManager(BlnkClient):
    """Manages Blnk API Key operations."""

    def __init__(self, config: LedgderServiceConfig) -> None:
        super().__init__(config, path="/api-keys")

    async def generate_api_key(self) -> Tuple[Any, Error]:
        """Placeholder for Generate API Key endpoint."""
        return await self._post(
            BlnkBase,  # Placeholder
        )


class BlnkGenericManager(BlnkClient):
    """Manages generic Blnk operations like metadata updates."""

    def __init__(self, config: LedgderServiceConfig) -> None:
        super().__init__(config, path="")  # Path is dynamic for /:id/metadata

    async def post_metadata(
        self, entity_id: str, request: PostMetadataRequest
    ) -> Tuple[Any, Error]:
        """Placeholder for Post MetaData endpoint."""
        return await self._post(
            BlnkBase,  # Placeholder
            path_suffix=f"/{entity_id}/metadata",
            data=request.model_dump(by_alias=True),
        )
