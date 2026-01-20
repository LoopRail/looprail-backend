import re
import typing
from enum import StrEnum
from typing import Annotated, Any, Literal, Union
from uuid import UUID

import phonenumbers
from pydantic import BeforeValidator, GetCoreSchemaHandler
from pydantic_core import core_schema
from pydantic_extra_types.phone_numbers import PhoneNumberValidator
from solders.pubkey import Pubkey

# from src.infrastructure import config
# from src.utils.country_utils import get_all_country_codes


_HEX_ADDRESS_REGEXP = re.compile("(0x)?[0-9a-f]{40}", re.IGNORECASE | re.ASCII)


def validate_address(v: str) -> str:
    if _HEX_ADDRESS_REGEXP.fullmatch(v):
        return v
    try:
        Pubkey(v)
        return v
    except ValueError:
        pass
    raise ValueError("Invalid EVM or Solana address")


DeletionFilter = Literal["all", "deleted", "active"]

# enabled_country_codes = get_all_country_codes(config.countries)

PhoneNumber = Annotated[
    Union[str, phonenumbers.PhoneNumber],
    PhoneNumberValidator(default_region="US"),
]

Address = Annotated[str, BeforeValidator(validate_address)]


class WorldLedger(StrEnum):
    WORLD_IN = "@world_in"
    WORLD_OUT = "@world_OUT"
    PAYCREST_FEES = "@paycrest_fees"
    PLATFORM_FEES = "@platform_fees"
    BLOCKCHAIN_FEES = "@blockchain_fees"


class IdentiyType(StrEnum):
    INDIVIDUAL = "individual"


class Chain(StrEnum):
    POLYGON = "polygon"
    BASE = "base"
    ETHEREUM = "ethereum"
    BITCOIN = "btc"


# New prefixed ID types


def _validate_id_with_prefix(v: str, expected_prefix: str) -> str:
    if not isinstance(v, str):
        raise TypeError("string required")
    if not v.startswith(expected_prefix):
        raise ValueError(f"ID must start with '{expected_prefix}'")
    return v


class PrefixedId(str):
    prefix: typing.ClassVar[str]

    def __new__(cls, value: str | UUID):
        if isinstance(value, UUID):
            value = str(value)

        if not isinstance(value, str):
            raise TypeError("ID must be a string or UUID")

        if not value.startswith(cls.prefix):
            value = f"{cls.prefix}{value}"

        return super().__new__(cls, value)

        # clean = value[len(cls.prefix) :]

        # # UUID validation
        # try:
        #     uuid.UUID(clean)
        # except ValueError:
        #     raise ValueError("ID suffix must be a valid UUID")

    def clean(self) -> str:
        return self[len(self.prefix) :]

    @classmethod
    def new[T](cls: T, value: str | UUID) -> T:
        """
        Create a prefixed ID from a raw or already-prefixed value
        """
        return cls(value)

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: Any, _handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls,
            core_schema.union_schema(
                [
                    core_schema.str_schema(),
                    core_schema.is_instance_schema(UUID),
                ]
            ),
        )


class UserId(PrefixedId):
    prefix = "usr_"


class WalletId(PrefixedId):
    prefix = "wlt_"


class AssetId(PrefixedId):
    prefix = "ast_"


class PaymentOrderId(PrefixedId):
    prefix = "pmt_"


class SessionId(PrefixedId):
    prefix = "ses_"


class RefreshTokenId(PrefixedId):
    prefix = "rft_"


class TransactionId(PrefixedId):
    prefix = "txn_"


class UserProfileId(PrefixedId):
    prefix = "usp_"


class OtpId(PrefixedId):
    prefix = "otp_"


class ReferenceId(PrefixedId):
    prefix = "ref_"


class OnBoardingTokenSub(PrefixedId):
    prefix = "onboarding_usr_"


class AccessTokenSub(PrefixedId):
    prefix = "access_ses_"


class ChallengeId(PrefixedId):
    prefix = "chl_"
