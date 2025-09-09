from fastapi import status, HTTPException, Depends, APIRouter

from ...schemas import user_schema
from .. import models, utils
from sqlalchemy.orm import Session
from ..database import get_db
from ..services.blockradar.blockradar_service import BlockradarService
from ...schemas.service_schema import GenerateAddressRequest



router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

@router.post("/", status_code=status.HTTP_201_CREATED, response_model = user_schema.UserOut)
async def create_user(user: user_schema.UserCreate, db: Session = Depends(get_db)):
    
    hashed_pwd = utils.hash(user.password)
    user.password = hashed_pwd
    
    new_user = models.User(**user.model_dump())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # generate wallet for the new user
    # service = BlockradarService(db)
    # generate_request = GenerateAddressRequest(
    #     label=f"user-{new_user.id}-wallet"  # adjust fields to match your schema
    # )

    # try:
    #     await service.generate_address(
    #         user_id=new_user.id,
    #         blockchain_slug=user.blockchain_slug,
    #         request=generate_request
    #     )
    # except Exception as e:
    #     raise HTTPException(
    #         status_code=500,
    #         detail=f"User created but wallet generation failed: {str(e)}"
    #     )

    return new_user

@router.get("/{id}", status_code=status.HTTP_201_CREATED, response_model = user_schema.UserOut)
def get_user(id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == id).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Post with id: {id} was NOT FOUND")
    
    return user
