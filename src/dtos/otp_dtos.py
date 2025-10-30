from pydantic import EmailStr
from src.dtos.base import Base


class OtpCreate(Base):
    email: EmailStr
