from pydantic import BaseModel, field_validator


class VerifyAccountResponse(BaseModel):
    status: str | bool
    message: str
    data: str

    @field_validator("data", mode="before")
    @classmethod
    def validate_data(cls, value: str):
        if not isinstance(value, str):
            return value["account_name"]
        return value
