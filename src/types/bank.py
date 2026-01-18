from typing import Dict, List, Optional

from pydantic import BaseModel


class Bank(BaseModel):
    name: str
    code: str
    type: str
    logo: Optional[str] = None
    id: Optional[str] = None


class SupportedBanksResponse(BaseModel):
    status: str
    data: Dict[str, List[Bank]]
