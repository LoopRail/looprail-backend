"""
Currently not being used
see src/types/common_types.py
"""

import re
from typing import Callable, Dict, Tuple

from src.types.error import Error, error


def validate_strip_leading_zero_11_to_10(
    cleaned_number: str, country: str
) -> Tuple[str | None, Error]:
    if cleaned_number.startswith("0"):
        if len(cleaned_number) == 11:
            return cleaned_number[1:], None
        return None, error(f"Invalid {country} phone number length")

    if len(cleaned_number) == 10:
        return cleaned_number, None

    return None, error(f"Invalid {country} phone number length")


def _validate_ng_number(cleaned_number: str) -> Tuple[str | None, Error]:
    """Validate and format a Nigerian phone number."""
    return validate_strip_leading_zero_11_to_10(cleaned_number, "Nigerian")


def _validate_us_number(cleaned_number: str) -> Tuple[str | None, Error]:
    """Validate and format a US phone number."""
    if len(cleaned_number) == 10:
        return cleaned_number
    if len(cleaned_number) == 11 and cleaned_number.startswith("1"):
        return cleaned_number[1:]
    return None, error("Invalid US phone number length")


def _validate_uk_number(cleaned_number: str) -> Tuple[str | None, Error]:
    """Validate and format a UK phone number."""
    return validate_strip_leading_zero_11_to_10(cleaned_number, "UK")


VALIDATORS: Dict[str, Callable[[str], str]] = {
    "NG": _validate_ng_number,
    "US": _validate_us_number,
    "UK": _validate_uk_number,
}


def validate_and_format_phone_number(
    number: str, country_code: str
) -> Tuple[str | None, Error]:
    """
    Validates and formats a phone number based on its country code.
    - Cleans the number by removing non-digit characters.
    - Applies country-specific validation rules.
    - Formats the number for storage (e.g., removing leading zeros).
    Returns the formatted number if valid, otherwise raises an error.
    """
    cleaned_number = re.sub(r"\D", "", number)
    country_code_upper = country_code.upper()

    validator = VALIDATORS.get(country_code_upper)

    if validator:
        return validator(cleaned_number)
    return cleaned_number
