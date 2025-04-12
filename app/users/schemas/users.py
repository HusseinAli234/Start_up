from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional


class UserBase(BaseModel):
    name: str
    about: str
    address: str
    email: EmailStr
    phone: str
    inn: str
    # Логотип, например, URL или путь к файлу
    logo: Optional[str] = None


class UserLoginSChema(BaseModel):
    email: EmailStr
    password: str


class UserCreate(BaseModel):
    name: str
    about: str
    address: str
    email: EmailStr
    phone: str
    inn: str
    logo: Optional[str] = None
    password: str = Field(min_length=8)

