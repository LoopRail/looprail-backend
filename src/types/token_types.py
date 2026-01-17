from typing import ClassVar

from pydantic import (BaseModel, ConfigDict, Field, field_serializer,
                      field_validator)

from src.types.common_types import SessionId, TokenSub, UserId
from src.types.types import TokenType
from src.utils.app_utils import kebab_case


class Token(BaseModel):
    __sub_prefix__: ClassVar[str]
    model_config = ConfigDict(
        from_attributes=True,
        extra="allow",
        arbitrary_types_allowed=True,
        alias_generator=kebab_case,
        populate_by_name=True,
    )
    sub: str 
    token_type: TokenType = Field(default=TokenType.ONBOARDING_TOKEN, alias="token")

    @field_serializer("sub")
    def serialize_sub_prefix(self, value: str) -> str:
        prefix = getattr(self, "__sub_prefix__", None)
        if prefix:
            return f"{prefix}_{value}"
        return value

    @field_validator("sub", mode="before")
    @classmethod
    def validate_sub(cls, v:str):
        if not v.startswith()



class OnBoardingToken(Token):
    __sub_prefix__ = "onboarding"
    user_id: UserId

    def get_clean_user_id(self) -> str:
        return self.user_id.removeprefix("usr_")


class AccessToken(Token):
    __sub_prefix__ = "access"
    user_id: UserId
    session_id: SessionId
    platform: str

    def get_clean_session_id(self) -> str:
        return self.session_id.removeprefix("ses_")
