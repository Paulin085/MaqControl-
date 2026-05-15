from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
import uuid

class UserBase(BaseModel):
    name: str = Field(..., min_length=2)
    email: str
    is_admin: bool = False
    permissions: List[str] = Field(default_factory=list)

class UserCreate(UserBase):
    password: str = Field(..., min_length=4)

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    is_admin: Optional[bool] = None
    permissions: Optional[List[str]] = None

class User(UserBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    hashed_password: str

    class Config:
        from_attributes = True
