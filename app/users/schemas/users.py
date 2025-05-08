from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime


class UserBase(BaseModel):
    name: str
    about: str
    address: str
    email: EmailStr
    phone: str
    inn: str
    logo: Optional[str] = None
    user_type: str  # "individual" или "company"
    is_active: bool
    expires_at: Optional[datetime]

class UserResponse(BaseModel):
    id: int
    class Config:   
        from_attributes = True

class UserLoginSChema(BaseModel):
    email: EmailStr
    password: str


class UserCreate(BaseModel):
    name: str
    about: Optional[str] = None
    address: Optional[str] = None
    email: EmailStr
    phone: Optional[str] = None
    inn: Optional[str] = None
    logo: Optional[str] = None
    password: str = Field(min_length=8)
    user_type: str 
    promo_code: str


