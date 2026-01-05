from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from src.types.types import TokenType
from src.utils.app_utils import kebab_case


class Token(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        extra="allow",
        arbitrary_types_allowed=True,
        alias_generator=kebab_case,
        populate_by_name=True,
    )
    sub: str
    token_type: TokenType = Field(
        default=TokenType.ONBOARDING_TOKEN, alias="token"
    )

    @field_serializer("sub")
    def serialize_sub_prefix(self, value: str) -> str:
        prefix = getattr(self, "__sub_prefix__", None)
        if prefix:
            return f"{prefix}_{value}"
        return value


class OnBoardingToken(Token):
    __sub_prefix__ = "onboarding"
    user_id: UUID


class AccessToken(Token):
    __sub_prefix__ = "access"
    sub: UUID
    session_id: UUID
    platform: str
