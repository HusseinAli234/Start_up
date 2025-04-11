# models.py
from app.models import Base
from sqlalchemy.orm import  Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, ForeignKey
from app.models.association import resume_job_association



class EmployerProfile(Base):
    __tablename__ = "employers"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    company_name: Mapped[str] = mapped_column(String, index=True)
    location: Mapped[str] = mapped_column(String, index=True)
    industry: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str] = mapped_column(String, index=True)

    job_postings: Mapped[list["JobPosting"]] = relationship(
        "JobPosting", back_populates="employer", cascade="all, delete-orphan",lazy="selectin"
    )



class JobPosting(Base):
    __tablename__ = "job_postings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str] = mapped_column(String, index=True)
    location: Mapped[str] = mapped_column(String, index=True)
    requirements: Mapped[str] = mapped_column(String,index=True)
    salary: Mapped[int] = mapped_column(Integer, index=True)
    employer_id: Mapped[int] = mapped_column(ForeignKey("employers.id"),nullable=True)

    employer: Mapped["EmployerProfile"] = relationship("EmployerProfile", back_populates="job_postings",lazy="selectin")
    skills: Mapped[list["VacancySkill"]] = relationship(
        "VacancySkill", back_populates="job", cascade="all, delete-orphan",lazy="selectin"
    )
    resumes = relationship(
        "Resume", secondary=resume_job_association, back_populates="job_postings",lazy="selectin"
    )


class VacancySkill(Base):
    __tablename__ = "vacancy_skill"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job_postings.id"))

    job: Mapped["JobPosting"] = relationship("JobPosting", back_populates="skills",lazy="selectin")
