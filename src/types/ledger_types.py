from typing import List

from pydantic import BaseModel, Field, field_validator

from src.types.error import error


class LedgerMetaData(BaseModel):
    description: str
    application: str


class Ledger(BaseModel):
    name: str
    ledger_id: str
    meta_data: LedgerMetaData

    @field_validator("ledger_id")
    @classmethod
    def validate_ledger_id(cls, val: str):
        if not val.startswith("ldg_"):
            raise error(f"Invalid ledger id {val}")
        return val


class LedgerConfig(BaseModel):
    ledgers: List[Ledger] = Field(default_factory=list)
