from decimal import Decimal

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from src.api.dependencies import (
    get_asset_repository,
    get_current_user_token,
    get_ledger_service,
    get_paystack_service,
    get_user_usecases,
    get_wallet_repository,
)
from src.dtos import (
    AssetBalance,
    UserAccountResponse,
    UserPublic,
    VerifyAccountResponse,
    WalletWithAssets,
)
from src.dtos.account_dtos import VerifyAccountRequest
from src.infrastructure.logger import get_logger
from src.infrastructure.repositories import AssetRepository, WalletRepository
from src.infrastructure.services import LedgerService, PaycrestService, PaystackService
from src.types import AccessToken, error
from src.usecases import UserUseCase

logger = get_logger(__name__)

router = APIRouter(prefix="/account", tags=["Auth"])


@router.get(
    "/me",
    response_model=UserAccountResponse,
    summary="Get current user account details",
)
async def get_user_account(
    token: AccessToken = Depends(get_current_user_token),
    user_usecases: UserUseCase = Depends(get_user_usecases),
    wallet_repo: WalletRepository = Depends(get_wallet_repository),
    asset_repo: AssetRepository = Depends(get_asset_repository),
    ledger_service: LedgerService = Depends(get_ledger_service),
):
    user, err = await user_usecases.get_user_by_id(user_id=token.get_clean_user_id())
    if err:
        return JSONResponse(status_code=404, content={"message": "User not found"})

    wallet, err = await wallet_repo.get_wallet_by_user_id(user_id=user.id)

    user_public = UserPublic.model_validate(user.model_dump())

    if not wallet:
        return UserAccountResponse(user=user_public, wallet=None)

    assets, err = await asset_repo.get_assets_by_wallet_id(wallet_id=wallet.id)
    if err:
        logger.error("Error fetching assets for wallet %s: %s", wallet.id, err.message)
        assets = []

    asset_balances = []
    for asset in assets:
        logger.debug("asset=%s, type=%s", asset, type(asset))
        balance_data = Decimal("0")

        if asset.ledger_balance_id:
            bal_resp, err = await ledger_service.balances.get_balance(
                asset.ledger_balance_id
            )
            print(bal_resp)
            if err:
                logger.error(
                    "Error fetching balance for asset %s (ledger_id: %s): %s",
                    asset.id,
                    asset.ledger_balance_id,
                    err.message,
                )
                continue
            balance_data = Decimal(str(bal_resp.balance))

        asset_balances.append(
            AssetBalance(
                asset_id=asset.get_prefixed_id(),
                name=asset.name,
                symbol=asset.symbol,
                decimals=asset.decimals,
                asset_type=asset.asset_type,
                balance=balance_data,
                network=asset.network,
                address=asset.address,
                standard=asset.standard,
                is_active=asset.is_active,
            )
        )

    wallet_with_assets = WalletWithAssets(
        id=wallet.get_prefixed_id(),
        address=wallet.address,
        chain=wallet.chain,
        provider=wallet.provider,
        is_active=wallet.is_active,
        assets=asset_balances,
    )

    return UserAccountResponse(user=user_public, wallet=wallet_with_assets)


@router.post("/verify", response_model=VerifyAccountResponse)
async def verify_account(
    verify_request: VerifyAccountRequest,
    paystack_service: PaystackService = Depends(get_paystack_service),
    # paycrest_service: PaycrestService = Depends(get_paycrest_service),
):
    logger.info(
        "Verifying account for account identifier: %s",
        verify_request.account_identifier,
    )
    # response, err = await paycrest_service.verify_account(
    #     account_number=verify_request.accountIdentifier,
    #     institution=verify_request.institution,
    # )
    #
    # if err is None:
    #     return response
    #
    # logger.error(
    #     "Error verifying account: %s using paycrest, falling to paystack, error code %s",
    #     err.message,
    #     err.code,
    # )
    response, err = await paystack_service.verify_account(
        account_number=verify_request.account_identifier,
        institution_code=verify_request.institution_code,
        country=verify_request.institution_country,
    )
    if err is None:
        return response

    logger.error(
        "Error verifying account: %s using paystack error code %s",
        err.message,
        err.code,
    )
    return JSONResponse(status_code=err.code, content={"message": err.message})


# TODO ping serices before making request
