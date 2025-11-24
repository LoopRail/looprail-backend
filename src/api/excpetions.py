from fastapi import HTTPException


class AuthError(HTTPException):
    pass


class OTPError(HTTPException):
    pass
