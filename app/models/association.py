from sqlalchemy import Table, Column, ForeignKey, Integer
from app.models.base import Base

resume_job_association = Table(
    "resume_job_association",
    Base.metadata,
    Column("resume_id", Integer, ForeignKey("resumes.id")),
    Column("job_posting_id", Integer, ForeignKey("job_postings.id")),
)


