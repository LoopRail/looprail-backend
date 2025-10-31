import random
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from src.models.otp import Otp
from src.utils.security import hash_otp
from src.utils.email_service import send_email_otp
from src.storage.otp_store import save_otp, get_otp, delete_otp
from src.types import OtpStatus, OtpType

router = APIRouter(prefix="/otp", tags=["OTP"])

class SendOtpRequest(BaseModel):
    email: EmailStr
    otp_type: OtpType = OtpType.EMAIL_VERIFICATION

class VerifyOtpRequest(BaseModel):
    email: EmailStr
    code: str
    otp_type: OtpType = OtpType.EMAIL_VERIFICATION


@router.post("/send")
def send_otp(req: SendOtpRequest):
    """Generate and send a new OTP."""
    code = str(random.randint(100000, 999999))
    hashed = hash_otp(code)
    otp = Otp(user_email=req.email, code_hash=hashed, otp_type=req.otp_type)
    save_otp(otp)

    send_email_otp(req.email, code)
    return {"message": "OTP sent successfully"}


@router.post("/verify")
def verify_otp(req: VerifyOtpRequest):
    """Verify an OTP against what is stored in Redis."""
    otp = get_otp(req.email, req.otp_type.value)
    if not otp:
        raise HTTPException(status_code=400, detail="No OTP found or expired")

    otp.attempts += 1

    if otp.is_expired():
        otp.status = OtpStatus.EXPIRED
        delete_otp(req.email, req.otp_type.value)
        raise HTTPException(status_code=400, detail="OTP expired")

    if otp.verify_code(req.code):
        otp.status = OtpStatus.VERIFIED
        delete_otp(req.email, req.otp_type.value)
        return {"message": "OTP verified successfully"}

    if otp.attempts > 3:
        otp.status = OtpStatus.BLOCKED
        delete_otp(req.email, req.otp_type.value)
        raise HTTPException(status_code=400, detail="Too many attempts")

    save_otp(otp)
    raise HTTPException(status_code=400, detail="Invalid OTP")
