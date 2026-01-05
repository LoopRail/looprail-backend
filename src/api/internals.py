from fastapi import HTTPException

from src.usecases import OtpUseCase


async def send_otp_internal(
    email: str,
    otp_usecases: OtpUseCase,
) -> str:
    _, err = await otp_usecases.get_user_token(user_email=email)
    if err and err != "Not found":
        raise HTTPException(status_code=500, detail="Server Error")

    err = await otp_usecases.delete_otp(user_email=email)
    if err and err != "Not found":
        raise HTTPException(status_code=500, detail="Server Error")

    otp_code, token, err = await otp_usecases.generate_otp(user_email=email)
    if err:
        raise HTTPException(status_code=400, detail=err.message)

    print(otp_code)  # send email here later
    # _, err = await resend_service.send_otp(
    #     to=otp_data.email,
    #     _from="team@looprail.com",
    #     otp_code=otp_code,
    # )
    # if err:
    #     logger.error("Failed to send OTP: %s", err)
    #     raise HTTPException(status_code=500, detail="Failed to send OTP.")
    #
    return token
