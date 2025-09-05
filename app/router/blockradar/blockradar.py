from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...database import get_db
from ...services.blockradar.blockradar_service import BlockradarService
from ....schemas.service_schema import GenerateAddressRequest, GenerateAddressResponse, AddressData
from ...models import Wallet

router = APIRouter(prefix="/blockradar", tags=["Blockradar"])

@router.post("/generate/{user_id}/{blockchain_slug}", response_model=GenerateAddressResponse)
async def generate_address(
    user_id: int,
    blockchain_slug: str,
    request: GenerateAddressRequest,
    db: Session = Depends(get_db),
):
    service = BlockradarService(db)
    try:
        wallet: Wallet = await service.generate_address(user_id, blockchain_slug, request)
        return GenerateAddressResponse(data=AddressData(address=wallet.address))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


