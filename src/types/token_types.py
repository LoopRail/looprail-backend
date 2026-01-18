from typing import ClassVar, Union

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from src.types.common_types import AccessTokenSub, OnBoardingTokenSub, SessionId, UserId
from src.types.error import ValidationError
from src.types.types import Platform, TokenType
from src.utils.app_utils import kebab_case


class Token(BaseModel):
    __sub_prefix__: ClassVar[str] = ""
    __expected_token_type__: ClassVar[TokenType]

    model_config = ConfigDict(
        from_attributes=True,
        extra="allow",
        arbitrary_types_allowed=True,
        alias_generator=kebab_case,
        populate_by_name=True,
        use_enum_values=True,
    )

    sub: Union[OnBoardingTokenSub, AccessTokenSub]
    token_type: TokenType = Field(default=TokenType.ONBOARDING_TOKEN, alias="token")

    @field_validator("sub", mode="before")
    @classmethod
    def validate_sub(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValidationError("Sub field must be a string")

        # Check if sub has the expected prefix
        if hasattr(cls, "__sub_prefix__") and cls.__sub_prefix__:
            expected_prefix = f"{cls.__sub_prefix__}"
            if not v.startswith(expected_prefix):
                raise ValidationError(
                    f"Invalid sub format. Expected to start with '{expected_prefix}', got: '{v}'"
                )

        return v

    @field_validator("token_type", mode="before")
    @classmethod
    def validate_token_type(cls, v: str | TokenType) -> TokenType:
        if isinstance(v, str):
            try:
                v = TokenType(v)
            except ValueError as e:
                raise ValidationError(f"Invalid token_type: '{v}'") from e

        # Check if token type matches expected type for this class
        if hasattr(cls, "__expected_token_type__"):
            if v != cls.__expected_token_type__:
                raise ValidationError(
                    message=f"Invalid token type."
                    f"Expected '{cls.__expected_token_type__.value}', got '{v.value}'"
                )

        return v

    @field_serializer("sub")
    def serialize_sub_prefix(self, value: str) -> str:
        prefix = getattr(self, "__sub_prefix__", None)
        if prefix and not value.startswith(prefix):
            return f"{prefix}{value}"
        return value

    def get_clean_sub(self) -> str:
        """Extract the UUID from the sub field"""
        return self.sub.removeprefix(f"{self.__sub_prefix__}")


class OnBoardingToken(Token):
    __sub_prefix__: ClassVar[str] = "onboarding_usr_"
    __expected_token_type__: ClassVar[TokenType] = TokenType.ONBOARDING_TOKEN

    token_type: TokenType = Field(default=TokenType.ONBOARDING_TOKEN, alias="token")
    user_id: UserId


class AccessToken(Token):
    __sub_prefix__: ClassVar[str] = "access_ses_"
    __expected_token_type__: ClassVar[TokenType] = TokenType.ACCESS_TOKEN

    token_type: TokenType = Field(default=TokenType.ACCESS_TOKEN, alias="token")
    user_id: UserId
    session_id: SessionId
    platform: Platform
