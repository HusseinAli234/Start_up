from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.employers import VacancySkill
from app.models.employers import JobPosting  
from app.schemas.vacancy_schema import VacancyCreate


class JobPostingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_job_posting(self, job_data: VacancyCreate) -> JobPosting:
        db_job = JobPosting(
            title=job_data.title,
            location=job_data.location,
            description=job_data.description,
            salary=job_data.salary,
            skills=[
                VacancySkill(
                    title=skill.title,
                )
                for skill in job_data.skills
            ]
        )
        self.db.add(db_job)
        await self.db.commit()
        await self.db.refresh(db_job)
        return db_job

    async def get_job_posting(self, job_id: int) -> JobPosting:
        result = await self.db.execute(
            select(JobPosting)
            .options(
                selectinload(JobPosting.skills),
                selectinload(JobPosting.resumes)
            )
            .where(JobPosting.id == job_id)
        )
        return result.scalars().first()

    async def delete_job_posting(self, job_id: int) -> JobPosting:
        job = await self.get_job_posting(job_id)
        if not job:
            return None
        await self.db.delete(job)
        await self.db.commit()
        return job
