from sqlalchemy import String,ForeignKey,Boolean,Integer,Column
from sqlalchemy.orm import relationship
from app.database import Base

class EmployerProfile(Base):
    __tablename__="employers"
    id = Column(Integer,primary_key=True,index=True)
    company_name=Column(String,index=True)
    location=Column(String,index=True)
    industry=Column(String,index=True)
    description=Column(String,index=True)
    job_posting=relationship('JobPosting',back_populates='employers')

class JobPosting(Base):
    __tablename__="job_postings"
    id = Column(Integer,primary_key=True,index=True)
    title=Column(String,index=True)
    description=Column(String,index=True)
    location=Column(String,index=True)
    salary=Column(Integer,index=True)
    employer_id=Column(Integer,ForeignKey('employers.id'))
    employer = relationship('EmployerProfile',back_populates='job_postings')
