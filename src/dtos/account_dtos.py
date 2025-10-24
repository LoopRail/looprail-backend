from enum import Enum
from typing import Optional, Tuple

from pydantic import BaseModel, Field, field_validator

from src.types.error import Error, error


class InstitutionCountry(Enum):
    NG = "nigeria"
    KY = "kenya"

    @classmethod
    def get(cls, key: str) -> Tuple[Optional["InstitutionCountry"], Error]:
        member = cls._member_map_.get(key)
        if member is None:
            return None, error(
                f"{key} is not a valid institution, should be 'bank' or 'mobile_money'"
            )
        return member, None


class VerifyAccountRequest(BaseModel):
    institution: str
    accountIdentifier: str = Field(
        serialization_alias="account-identifier", validation_alias="account-identifier"
    )
    institutionCountry: str = Field(
        serialization_alias="institution-country",
        validation_alias="institution-country",
    )
    institutionCode: str | None = Field(
        serialization_alias="institution-code",
        validation_alias="institution-code",
        default=None,
    )

    @field_validator("institutionCountry")
    @classmethod
    def validate_institusion_country(cls, v: str):
        _, err = InstitutionCountry.get(v.upper())
        if err is not None:
            raise err
        return v
