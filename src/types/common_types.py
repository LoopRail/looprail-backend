from typing import Annotated, Literal, Union

import phonenumbers
from pydantic_extra_types.phone_numbers import PhoneNumberValidator

from src.infrastructure import config
from src.utils.country_utils import get_all_country_codes

DeletionFilter = Literal["all", "deleted", "active"]

enabled_country_codes = get_all_country_codes(config.countries)

CommonPhoneNumber = Annotated[
    Union[str, phonenumbers.PhoneNumber],
    PhoneNumberValidator(supported_regions=enabled_country_codes, default_region="US"),
]
