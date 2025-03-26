from pydantic import BaseModel, EmailStr, Field,List

class ResumePdf(BaseModel):
    id: int
    