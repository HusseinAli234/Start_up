
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.job_seekers import Resume, Education, Experience, Skill, TypeSkill,HardTotal
from app.schemas.resume_schema import ResumeCreate
from sqlalchemy.orm import selectinload
from sqlalchemy import delete
from app.models.employers import JobPosting
from fastapi import FastAPI, HTTPException
from app.users.models import User
from fastapi import status


app = FastAPI()


class ResumeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_resume(self, resume_data: ResumeCreate, user: User, vacancy_id: int | None = None) -> Resume:
        db_resume = Resume(
            fullname=resume_data.fullname,
            location=resume_data.location,
        )
        if resume_data.hard_total:
            db_hard_total = HardTotal(
            total=resume_data.hard_total.total,
            justification=resume_data.hard_total.justification,
            resume=db_resume
        )
        db_resume.hard_total = db_hard_total
       

        db_resume.experiences = [
                Experience(name=exp.name, description=exp.description, resume=db_resume)
                for exp in resume_data.experience
            ]
        db_resume.educations = [
                Education(name=edu.name, description=edu.description, resume=db_resume)
                for edu in resume_data.education
            ]
        db_resume.skills = [
                Skill(
                    title=skill.title,
                    level=skill.level,
                    justification=skill.justification,
                    type=TypeSkill(skill.type),
                    resume=db_resume
                )
                for skill in resume_data.skills
            ],
        db_resume.user_id = user.id
        with self.db.no_autoflush:
            self.db.add(db_resume)   
            self.db.add(db_resume.hard_total) 
            self.db.add_all(db_resume.experiences)
            self.db.add_all(db_resume.educations)
            self.db.add_all(db_resume.skills)
        if vacancy_id:
            # Если задан id вакансии, пытаемся получить вакансию
            job = await self.db.get(JobPosting, vacancy_id)
            if not job:
                raise HTTPException(status_code=404, detail="Vacancy not found")
            if job.user_id != user.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                    detail="You don't have permission to attach this vacancy")
            db_resume.job_postings.append(job)

        self.db.add(db_resume)
        await self.db.commit()  # асинхронный commit
        await self.db.refresh(db_resume)  # обновляем объект после сохранения
        return db_resume

    async def resume_skill_add(self, resume_id: int, soft_skills: dict):
        # Проверка на существование резюме
        result = await self.db.execute(select(Resume).where(Resume.id == resume_id))
        resume = result.scalar_one_or_none()

        if resume is None:
            raise ValueError(f"Resume with id {resume_id} not found")

        # Обновляем soft_total или создаём, если его ещё нет
        soft_total_data = soft_skills.get("soft_total")
        if soft_total_data:
            if resume.soft_total:
                resume.soft_total.total = soft_total_data["total"]
                resume.soft_total.justification = soft_total_data["justification"]
            else:
                from app.models.job_seekers import SoftTotal  # импорт тут, если нет глобального
                resume.soft_total = SoftTotal(
                    total=soft_total_data["total"],
                    justification=soft_total_data["justification"],
                    resume_id=resume_id
                )

        # Получаем список новых soft-skills
        skills_to_add_data = soft_skills.get("skills", [])

        skills = []
        for skill in skills_to_add_data:
            skill_obj = Skill(
                title=skill["title"],
                level=skill["level"],
                justification=skill["justification"],
                type=TypeSkill.SOFT,
                resume_id=resume_id
            )
            skills.append(skill_obj)

        # Добавляем в сессию
        self.db.add_all(skills)
        await self.db.commit()
    async def get_resume(self, resume_id: int, user: User) -> Resume:
    # Используем selectinload для предзагрузки связанных объектов
        result = await self.db.execute(
            select(Resume)
            .filter_by(id=resume_id, user_id=user.id)
            .options(
                selectinload(Resume.experiences),
                selectinload(Resume.educations),
                selectinload(Resume.skills)
            )
            .where(Resume.id == resume_id)
        )
        resume = result.scalars().first()
        return resume

    async def delete_resume(self, resume_id: int, user: User) -> Resume:
        resume = await self.get_resume(resume_id, user)
        if not resume:
            return None
        await self.db.delete(resume)
        await self.db.commit()
        return resume
