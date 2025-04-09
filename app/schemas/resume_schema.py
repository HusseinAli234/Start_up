# schemas.py
from pydantic import BaseModel
from enum import Enum
from typing import List


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
    level: int
    justification: str
    type: SkillType


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
    resumes: List[JobShort] = []

class ResumeResponse(BaseModel):
    id: int
    fullname: str
    location: str
    skills: List[SkillSchema] 
    educations: List[EducationSchema]  
    experiences: List[ExperienceSchema] 

    class Config:
        orm_mode = True
