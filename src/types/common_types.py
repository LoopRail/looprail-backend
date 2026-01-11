import re
from enum import Enum
from typing import Annotated, Literal, Union

import phonenumbers
from pydantic import BeforeValidator
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


class WorldLedger(str, Enum):
    WORLD = "@world"
    PAYCREST_FEES = "@paycrest_fees"
    PLATFORM_FEES = "@platform_fees"
    BLOCKCHAIN_FEES = "@blockchain_fees"


class IdentiyType(str, Enum):
    INDIVIDUAL = "individual"


class Chain(str, Enum):
    POLYGON = "polygon"
    BASE = "base"
    ETHEREUM = "ethereum"
    BITCOIN = "btc"
