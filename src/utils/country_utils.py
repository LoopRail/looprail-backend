from typing import List
from src.types.country_types import CountriesData, CountryInfo


def is_valid_country_code(countries: CountriesData, /, country_code: str) -> bool:
    country: CountryInfo | None = countries.countries.get(country_code.upper())
    return country is not None and country.enabled


def get_country_info(
    countries: CountriesData, /, country_code: str
) -> CountryInfo | None:
    return countries.countries.get(country_code.upper())


def get_all_country_codes(countries: CountriesData) -> List[str]:
    """
    Returns a list of all enabled country codes.
    """
    return [code for code, info in countries.countries.items() if info.enabled]
