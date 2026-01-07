from typing import Annotated, Literal, Union

import phonenumbers
from pydantic_extra_types.phone_numbers import PhoneNumberValidator

DeletionFilter = Literal["all", "deleted", "active"]

CommonPhoneNumber = Annotated[
    Union[str, phonenumbers.PhoneNumber],
    PhoneNumberValidator(supported_regions=["US"], default_region="US"),
]
