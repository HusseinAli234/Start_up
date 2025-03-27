from pydantic import BaseModel, EmailStr, Field
from enum import Enum
from typing import List

class SkillType(str, Enum):
    HARD = "HARD"
    SOFT = "SOFT"

class Skill(BaseModel):
    title: str
    level: int
    justification: str
    type: SkillType

class Education(BaseModel):
    name: str
    description: str
class Experience(BaseModel):
    name: str    
    description: str


class ResumeCreate(BaseModel):
    fullname: str
    location: str
    experience: List[Experience]
    education: List[Education]
    skills: List[Skill]

class ResumeResponse(BaseModel):
    fullname: str
    class Config:
        orm_mode = True
