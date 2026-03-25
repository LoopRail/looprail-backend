from typing import Tuple

import phonenumbers

from src.types.country_types import CountriesData
from src.types.error import Error, error


def is_phone_number_from_allowed_country(
    phone_number: str, allowed_countries: CountriesData
) -> Tuple[bool, Error]:
    """
    Checks if a phone number belongs to one of the enabled countries
    by matching its dial code against enabled country dial codes.
    """
    try:
        parsed = phonenumbers.parse(phone_number)
    except phonenumbers.NumberParseException:
        return False, error("Invalid phone number")

    country_code_str = f"+{parsed.country_code}"

    for info in allowed_countries.countries.values():
        if info.enabled and info.dial_code == country_code_str:
            return True, None

    return False, error("Phone number country is not supported")
