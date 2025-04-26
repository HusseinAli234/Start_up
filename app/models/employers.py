# models.py
from app.models.base import Base
from sqlalchemy.orm import  Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, ForeignKey
from app.models.association import resume_job_association
from app.users.models.users import User


class JobPosting(Base):
    __tablename__ = "job_postings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str] = mapped_column(String, index=True)
    location: Mapped[str] = mapped_column(String, index=True)
    requirements: Mapped[str] = mapped_column(String,index=True)
    salary: Mapped[str] = mapped_column(String, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped["User"] = relationship("User", back_populates="user_job_postings",lazy="selectin")

    skills: Mapped[list["VacancySkill"]] = relationship(
        "VacancySkill", 
        back_populates="job", 
        cascade="all, delete-orphan",lazy="selectin"
    )
    resumes = relationship(
        "Resume", 
        secondary=resume_job_association, 
        back_populates="job_postings",lazy="selectin"
    )



class VacancySkill(Base):
    __tablename__ = "vacancy_skill"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job_postings.id"))

    job: Mapped["JobPosting"] = relationship("JobPosting", back_populates="skills",lazy="selectin")
