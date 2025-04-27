# models.py
import enum
from sqlalchemy.orm import  Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Float, ForeignKey, Enum as SAEnum,Boolean
from app.models.base import Base
from app.models.association import resume_job_association     
from app.users.models.users import User


class TypeSkill(enum.Enum):
    SOFT = "SOFT"
    HARD = "HARD"
    TEST = "TEST"
    FEEDBACK="FEEDBACK"


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    fullname: Mapped[str] = mapped_column(String, index=True)
    location: Mapped[str] = mapped_column(String, index=True)
    cv_gcs_uri: Mapped[str] = mapped_column(String, nullable=True)
    hard_total: Mapped["HardTotal"] = relationship("HardTotal", back_populates="resume", uselist=False, cascade="all, delete-orphan", lazy="selectin")
    soft_total: Mapped["SoftTotal"] = relationship("SoftTotal", back_populates="resume", uselist=False, cascade="all, delete-orphan", lazy="selectin")
    test_total: Mapped["TestTotal"] = relationship("TestTotal", back_populates="resume", uselist=False, cascade="all, delete-orphan", lazy="selectin")

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'))
    
    skills: Mapped[list["Skill"]] = relationship(
        "Skill", 
        back_populates="resume", 
        cascade="all, delete-orphan",lazy="selectin"
    )
    educations: Mapped[list["Education"]] = relationship(
        "Education", 
        back_populates="resume", 
        cascade="all, delete-orphan",lazy="selectin"
    )
    experiences: Mapped[list["Experience"]] = relationship(
        "Experience",
        back_populates="resume", 
        cascade="all, delete-orphan",lazy="selectin"
    )
    job_postings = relationship(
        "JobPosting", 
        secondary=resume_job_association, 
        back_populates="resumes",lazy="selectin"
    )
   
    user: Mapped["User"] = relationship("User", back_populates="user_resumes",lazy="selectin")



class Education(Base):
    __tablename__ = "educations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str] = mapped_column(String, index=True)
    resume_id: Mapped[int] = mapped_column(Integer, ForeignKey("resumes.id"))
    resume: Mapped["Resume"] = relationship("Resume", back_populates="educations",lazy="selectin")


class Experience(Base):
    __tablename__ = "experiences"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str] = mapped_column(String, index=True)
    resume_id: Mapped[int] = mapped_column(Integer, ForeignKey("resumes.id"))
    resume: Mapped["Resume"] = relationship("Resume", back_populates="experiences",lazy="selectin")

class HardTotal(Base):
    __tablename__ = "hard_skills"
    id: Mapped[int] = mapped_column(Integer,primary_key=True,autoincrement=True)
    total: Mapped[float] = mapped_column(Float,index=True)
    justification: Mapped[str] = mapped_column(String,index=True)
    resume_id: Mapped[int] = mapped_column(Integer, ForeignKey("resumes.id"), unique=True)
    resume: Mapped["Resume"] = relationship("Resume", back_populates="hard_total", lazy="selectin")

class SoftTotal(Base):
    __tablename__ = "soft_skills"
    id: Mapped[int] = mapped_column(Integer,primary_key=True,autoincrement=True)
    total: Mapped[float] = mapped_column(Float,index=True,default=0)
    justification: Mapped[str] = mapped_column(String,index=True)
    resume_id: Mapped[int] = mapped_column(Integer, ForeignKey("resumes.id"), unique=True)
    resume: Mapped["Resume"] = relationship("Resume", back_populates="soft_total", lazy="selectin")

class TestTotal(Base):
    __tablename__ = "test_skills"
    id: Mapped[int] = mapped_column(Integer,primary_key=True,autoincrement=True)
    total: Mapped[float] = mapped_column(Float,index=True)
    resume_id: Mapped[int] = mapped_column(Integer, ForeignKey("resumes.id"), unique=True)
    resume: Mapped["Resume"] = relationship("Resume", back_populates="test_total", lazy="selectin")


class Skill(Base):
    __tablename__ = "resume_skills"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    level: Mapped[float] = mapped_column(Float, index=True)
    justification: Mapped[str] = mapped_column(String, index=True)
    resume_id: Mapped[int] = mapped_column(Integer, ForeignKey("resumes.id"))
    type: Mapped[TypeSkill] = mapped_column(SAEnum(TypeSkill), nullable=False, default=TypeSkill.HARD)
    
    resume: Mapped["Resume"] = relationship("Resume", back_populates="skills",lazy="selectin")
class SocialTest(Base):
    __tablename__ = "social_test"
    id: Mapped[int] = mapped_column(Integer,primary_key=True,autoincrement=True)
    title: Mapped[str] = mapped_column(String,index=True)
    is_Optional:Mapped[bool] = mapped_column(Boolean,index=True,nullable=True)
    proffesion:Mapped[str] = mapped_column(String,index=True,nullable=True)
    # methodology:Mapped[str] = mapped_column(String,index=True,nullable=True)
    questions: Mapped[list["TestQuestion"]] = relationship(
        "TestQuestion",
        back_populates="social_test", 
        cascade="all, delete-orphan",lazy="selectin"
    )
    user: Mapped["User"] = relationship("User", back_populates="user_test",lazy="selectin")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'))



class TestQuestion(Base):
    __tablename__ = "test_question"
    id: Mapped[int] = mapped_column(Integer,primary_key=True,autoincrement=True)
    question: Mapped[str] = mapped_column(String,index=True)
    mark:Mapped[int] = mapped_column(Integer,index=True,nullable=True)
    source:Mapped[str] = mapped_column(String,index=True,nullable=True)
    test_id:Mapped[int] = mapped_column(Integer,ForeignKey("social_test.id"))
    social_test: Mapped["SocialTest"] = relationship("SocialTest",back_populates="questions",lazy="selectin") 
       
