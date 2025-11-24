from pydantic import BaseModel, ConfigDict


class baseBlockRaderType(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, extra="allow", arbitrary_types_allowed=True
    )


class baseResponse(baseBlockRaderType):
    message: str
    statusCode: int
