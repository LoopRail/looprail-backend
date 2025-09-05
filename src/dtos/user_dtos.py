from uuid import UUID

from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    email: str


class UserPublic(BaseModel):
    id: UUID
    username: str
    email: str
    first_name: str
    last_name: str

    class Config:
        from_attributes = True
