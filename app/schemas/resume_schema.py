# schemas.py
from pydantic import BaseModel
from enum import Enum
from typing import List
from typing import Optional


class JobShort(BaseModel):
    id: int
    title: str

    class Config:
        orm_mode = True

class SkillType(str, Enum):
    HARD = "HARD"
    SOFT = "SOFT"


class SkillSchema(BaseModel):
    title: str
    level: float
    justification: str
    type: SkillType

class HardTotal(BaseModel):
    total:int
    justification:str
    class Config:
        orm_mode = True

class TestTotal(BaseModel):
    total:float
    class Config:
        orm_mode = True

class SoftTotal(BaseModel):
    total:int
    justification:str
    class Config:
        orm_mode = True
class EducationSchema(BaseModel):
    name: str
    description: str


class ExperienceSchema(BaseModel):
    name: str
    description: str


class ResumeCreate(BaseModel):
    fullname: str
    location: str
    experience: List[ExperienceSchema]
    education: List[EducationSchema]
    skills: List[SkillSchema]
    hard_total: Optional[HardTotal]
    resumes: List[JobShort] = []

class ResumeResponse(BaseModel):
    id: int
    fullname: str
    location: str
    hard_total: Optional[HardTotal]
    soft_total: Optional[SoftTotal]
    test_total: Optional[TestTotal]
    skills: List[SkillSchema] 
    educations: List[EducationSchema]  
    experiences: List[ExperienceSchema] 

    class Config:
        orm_mode = True
