from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from statistics import mean
from app.models.employers import VacancySkill
from app.models.employers import JobPosting  
from app.schemas.vacancy_schema import VacancyCreate
from app.models.job_seekers import Resume
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
    async def sort_by_hard(self, job_id: int):
        result = await self.db.execute(
            select(JobPosting)
            .options(
                selectinload(JobPosting.skills),
                selectinload(JobPosting.resumes).selectinload(Resume.skills)
            )
            .where(JobPosting.id == job_id)
        )

        job_posting = result.scalars().first()
        if not job_posting:
            return []

        # Названия скиллов у вакансии
        vacancy_skill_titles = {skill.title.lower() for skill in job_posting.skills}

        resume_scores = []

        for resume in job_posting.resumes:
            matched_skills = [
                skill.level for skill in resume.skills
                if skill.title.lower() in vacancy_skill_titles
            ]
            avg_score = mean(matched_skills) if matched_skills else 0
            resume_scores.append((resume, avg_score))

        # Сортировка по среднему баллу (по убыванию)
        sorted_resumes = sorted(resume_scores, key=lambda item: item[1], reverse=True)

        return [{"resume": r.fullname, "avg_skill_score": score} for r, score in sorted_resumes]
    async def delete_job_posting(self, job_id: int) -> JobPosting:
        job = await self.get_job_posting(job_id)
        if not job:
            return None
        await self.db.delete(job)
        await self.db.commit()
        return job
