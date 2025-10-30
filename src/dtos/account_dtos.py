from enum import Enum

from pydantic import Field

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
