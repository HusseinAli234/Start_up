from pydantic import BaseModel
from enum import Enum
from typing import List
from typing import Optional

class Question(BaseModel):
    question: str
    mark: Optional[int]
    source:Optional[str]
    class Config:
        orm_mode = True   

class CreateTest(BaseModel):
    title: str
    proffesion:str
    isOptional:bool
    # methodology:str
    questions: List[Question]

class ResponseTest(BaseModel):
    id: int
    title: str
    proffesion:str
    is_Optional:bool
    # methodology:str
    questions: List[Question]
    class Config:
        orm_mode = True  

class SubTest(BaseModel):
    title:str
    result:Optional[float]
    # test_id:f
    is_Optional: Optional[bool]
    maximum:Optional[float]

class ResultOfTest(BaseModel):
    resume_id:int
    sub_tests:List[SubTest]
    
