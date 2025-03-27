from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String,ForeignKey,Boolean,Enum,Float
from app.database import Base
import enum
class TypeSkill(enum.Enum):
    SOFT = "SOFT"
    HARD = "HARD"

class Resume(Base):
    __tablename__ = "resumes"
    id = Column(Integer, primary_key=True, index=True,autoincrement=True)
    full_name = Column(String, index=True)
    location = Column(String,index=True)
    skills=relationship('Skill',back_populates='resumes')
    educations=relationship('Education',back_populates='resumes')
    experience=relationship('Experience',back_populates='resumes')
    isActive=Column(Boolean,index=True)


class Education(Base):
    __tablename__='educations'
    id = Column(Integer,primary_key=True,index=True,autoincrement=True)
    name = Column(String,index=True)
    description = Column(String,index=True)
    resume_id=Column(Integer,ForeignKey('resumes.id'))
    resume=relationship('Resume',back_populates='educations')

class Experience(Base):
    __tablename__='experiences'
    id = Column(Integer,primary_key=True,index=True,autoincrement=True)
    name = Column(String,index=True)
    description = Column(String,index=True)

    resume_id=Column(Integer,ForeignKey('resumes.id'))
    resume=relationship('Resume',back_populates='experiences')    


class Skill(Base):
    __tablename__='skills'
    id = Column(Integer,primary_key=True,autoincrement=True)
    title = Column(String,nullable=False)
    level = Column(Float,index=True)
    justification = Column(String,index=True)
    resume_id=Column(Integer,ForeignKey('resumes.id'))
    resume = relationship('Resume',back_populates='skills')
    type = Column(Enum(TypeSkill), nullable=False, default=TypeSkill.HARD)  

