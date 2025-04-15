from pydantic import BaseModel
from enum import Enum
from typing import List
from typing import Optional

class Question(BaseModel):
    question: str
    mark: int
    class Config:
        orm_mode = True   

class CreateTest(BaseModel):
    title: str
    proffesion:str
    questions: List[Question]

class ResponseTest(BaseModel):
    id: int
    title: str
    proffesion:str
    questions: List[Question]
    class Config:
        orm_mode = True  

class SubTest(BaseModel):
    title:str
    result:float

class ResultOfTest(BaseModel):
    resume_id:int
    sub_tests:List[SubTest]
    
