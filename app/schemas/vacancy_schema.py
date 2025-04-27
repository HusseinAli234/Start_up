from pydantic import BaseModel
from enum import Enum
from typing import List

class ResumeShort(BaseModel):
    id: int
    fullname: str

    class Config:
        orm_mode = True
class SkillSchema(BaseModel):
    title: str

class VacancyCreate(BaseModel):
    title: str
    location: str
    description: str
    requirements: str
    salary: str
    skills: List[SkillSchema]
    resumes: List[ResumeShort] = []

class VacancyResponse(BaseModel):
    id: int
    title: str
    location: str
    requirements: str
    skills: List[SkillSchema] 
    description: str 
    resumes: List[ResumeShort] = []

    class Config:
        orm_mode = True
class SortResumesResponse(BaseModel):
    resume: str
    avg_skill_score: float    