from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String,ForeignKey,Boolean,Enum,Float
from app.database import Base
import enum
class TypeSkill(enum.Enum):
    SOFT = "SOFT"
    WORKER = "HARD"

class Resume(Base):
    __tablename__ = "resumes"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    location = Column(String,index=True)
    experience = Column(String,index=True)
    education = Column(String,index=True)
    skills=relationship('Skill',back_populates='resumes')
    isActive=Column(Boolean,index=True)
class Skill(Base):
    __tablename__='skills'
    id = Column(Integer,primary_key=True)
    title = Column(String,nullable=False)
    level = Column(Float,index=True)
    justification = Column(String,index=True)
    resume_id=Column(Integer,ForeignKey('resumes.id'))
    resume = relationship('Resume',back_populates='skills')
    type = Column(Enum(TypeSkill), nullable=False, default=TypeSkill.HARD)  

