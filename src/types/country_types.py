from typing import Dict

from pydantic import BaseModel


class CountryInfo(BaseModel):
    name: str
    iso2: str
    iso3: str
    dial_code: str
    currency: str
    enabled: bool


class CountriesData(BaseModel):
    countries: Dict[str, CountryInfo]
