from typing import Annotated, Literal, Union

import phonenumbers
from pydantic import BeforeValidator
from pydantic_extra_types.phone_numbers import PhoneNumberValidator
from solana.publickey import PublicKey
from web3 import Web3

from src.infrastructure import config
from src.utils.country_utils import get_all_country_codes


def validate_address(v: str) -> str:
    if Web3.is_address(v):
        return v
    try:
        PublicKey(v)
        return v
    except ValueError:
        pass
    raise ValueError("Invalid EVM or Solana address")


DeletionFilter = Literal["all", "deleted", "active"]

enabled_country_codes = get_all_country_codes(config.countries)

PhoneNumber = Annotated[
    Union[str, phonenumbers.PhoneNumber],
    PhoneNumberValidator(supported_regions=enabled_country_codes, default_region="US"),
]

Address = Annotated[str, BeforeValidator(validate_address)]
