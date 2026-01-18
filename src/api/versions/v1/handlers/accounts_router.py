from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from src.api.dependencies import get_paycrest_service, get_paystack_service
from src.dtos import VerifyAccountResponse
from src.dtos.account_dtos import VerifyAccountRequest
from src.infrastructure.logger import get_logger
from src.infrastructure.services import PaycrestService, PaystackService

logger = get_logger(__name__)

router = APIRouter(prefix="/account", tags=["Auth"])

@router.get("/me")
async def get_user_account():
    pass

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
