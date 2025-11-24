from pydantic import BaseModel, ConfigDict

from src.utils import kebab_case


class AccessToken(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        extra="allow",
        arbitrary_types_allowed=True,
        alias_generator=kebab_case,
    )
    sub: str



