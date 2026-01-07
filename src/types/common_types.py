import re
from typing import Annotated, Literal, Union

import phonenumbers
from pydantic import BeforeValidator
from pydantic_extra_types.phone_numbers import PhoneNumberValidator
from solana.publickey import PublicKey

from src.infrastructure import config
from src.utils.country_utils import get_all_country_codes

_HEX_ADDRESS_REGEXP = re.compile("(0x)?[0-9a-f]{40}", re.IGNORECASE | re.ASCII)


def validate_address(v: str) -> str:
    # Validate as EVM address using regex
    if _HEX_ADDRESS_REGEXP.fullmatch(v):
        return v
    # Validate as Solana address
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
