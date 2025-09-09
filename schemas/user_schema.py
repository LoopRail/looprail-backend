from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime
    # blockchain_slug: str
    
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    # blockchain_slug: str  # Added blockchain_slug field for dynamic wallet generation
    
class UserLogin(BaseModel):
    email: EmailStr
    password: str
    
class Token(BaseModel):
    access_token: str
    token_type: str
    
class TokenData(BaseModel):
    id: Optional[int] = None
