from enum import Enum

from pydantic import Field, field_validator

from src.dtos.base import Base


class InstitutionCountry(str, Enum):
    NG = "NG"
    KY = "KY"


class VerifyAccountRequest(Base):
    institution: str
    account_identifier: str
    institution_code: str | None = Field(
        default=None,
    )
    institution_country: InstitutionCountry


class VerifyAccountResponse(Base):
    status: str | bool
    message: str
    data: str

    @field_validator("data", mode="before")
    @classmethod
    def validate_data(cls, value: str):
        if not isinstance(value, str):
            return value["account_name"]
        return value
