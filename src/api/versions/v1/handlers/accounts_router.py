from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from src.api.dependencies import (
    get_asset_repository,
    get_blockrader_wallet_service,
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
from src.infrastructure.services import LedgerService, PaystackService
from src.types import AccessToken, AssetId
from src.usecases import UserUseCase, WalletService

logger = get_logger(__name__)

router = APIRouter(prefix="/account", tags=["Accounts"])


@router.get(
    "/me",
    response_model=UserAccountResponse,
    summary="Get current user account details",
)
async def get_user_account(
    token: AccessToken = Depends(get_current_user_token),
    user_usecases: UserUseCase = Depends(get_user_usecases),
    wallet_service: WalletService = Depends(get_blockrader_wallet_service),
):
    user, err = await user_usecases.get_user_by_id(user_id=token.user_id.clean())
    if err:
        return JSONResponse(status_code=404, content={"message": "User not found"})

    wallet_with_assets, err = await wallet_service.get_wallet_with_assets(
        user_id=token.user_id
    )

    if err:
        return JSONResponse(status_code=500, content={"message": err.message})

    user_public = UserPublic.model_validate(user.model_dump())

    return UserAccountResponse(user=user_public, wallet=wallet_with_assets)


@router.get(
    "/balance",
    response_model=WalletWithAssets,
    summary="Get current user wallet balance",
)
async def get_user_balance(
    token: AccessToken = Depends(get_current_user_token),
    wallet_service: WalletService = Depends(get_blockrader_wallet_service),
):
    wallet_with_assets, err = await wallet_service.get_wallet_with_assets(
        user_id=token.user_id
    )

    if err:
        return JSONResponse(status_code=500, content={"message": err.message})

    if not wallet_with_assets:
        return JSONResponse(status_code=404, content={"message": "Wallet not found"})

    return wallet_with_assets


@router.get(
    "/balance/{asset_id}",
    response_model=AssetBalance,
    summary="Get current user specific asset balance",
)
async def get_asset_balance(
    asset_id: AssetId,
    token: AccessToken = Depends(get_current_user_token),
    wallet_service: WalletService = Depends(get_blockrader_wallet_service),
):
    asset_balance, err = await wallet_service.get_asset_balance(
        user_id=token.user_id, asset_id=asset_id
    )
    if err:
        return JSONResponse(status_code=404, content={"message": err.message})

    return asset_balance


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
