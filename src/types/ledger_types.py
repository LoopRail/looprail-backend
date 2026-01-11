from typing import List, Optional, Tuple

from pydantic import BaseModel, Field, field_validator

from src.types.error import Error, error


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

    def get_ledger(self, ledger_name: str) -> Tuple[Optional[Ledger], Error]:
        for ledger in self.ledgers:
            if ledger.name == ledger_name:
                return ledger, None
        return None, error(f"Ledger with name {ledger_name} not found")
