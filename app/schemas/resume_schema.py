from pydantic import BaseModel, EmailStr, Field,List
from enum import Enum
class SkillType(str, Enum):
    HARD = "HARD"
    SOFT = "SOFT"

class Skill(BaseModel):
    id: int
    title: str
    level: float = Field(gt=0.0, le=1.0)
    justification: str
    type: SkillType

class Resume(BaseModel):
    id: int
    fullname: str
    location: str
    experience: str
    education: str
    skills: List[Skill]

class ResumeRequest(BaseModel):
    fullname: str
    location: str
    experience: str
    education: str

class ResumeResponse(BaseModel):
    id: int
    fullname: str
    class Config:
        orm_mode = True
