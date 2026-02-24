from pydantic import BaseModel, ConfigDict

from src.utils.string_utils import camel_case


class basePaycrestType(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        alias_generator=camel_case,
        populate_by_name=True,
    )


class basePaycrestResponse(basePaycrestType):
    status: str
    message: str
