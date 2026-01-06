from typing import List
from pydantic import BaseModel, Field


class LedgerMetaData(BaseModel):
    description: str
    application: str


class LedgerConfig(BaseModel):
    name: str
    meta_data: LedgerMetaData


class LedgerSettings(BaseModel):
    ledgers: List[LedgerConfig] = Field(default_factory=list)
