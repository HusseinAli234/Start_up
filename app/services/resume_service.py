# resume_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.job_seekers import Resume, Education, Experience, Skill, TypeSkill
from app.schemas.resume_schema import ResumeCreate
from sqlalchemy.orm import selectinload
from sqlalchemy import delete

class ResumeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_resume(self, resume_data: ResumeCreate) -> Resume:
        db_resume = Resume(
            fullname=resume_data.fullname,
            location=resume_data.location,
            experiences=[
                Experience(name=exp.name, description=exp.description)
                for exp in resume_data.experience
            ],
            educations=[
                Education(name=edu.name, description=edu.description)
                for edu in resume_data.education
            ],
            skills=[
                Skill(
                    title=skill.title,
                    level=skill.level,
                    justification=skill.justification,
                    type=TypeSkill(skill.type)
                )
                for skill in resume_data.skills
            ]
        )
        self.db.add(db_resume)
        await self.db.commit()  # commit должен быть асинхронным
        await self.db.refresh(db_resume)  # обновление объекта после сохранения
        return db_resume

    async def get_resume(self, resume_id: int) -> Resume:
    # Используем selectinload для предзагрузки связанных объектов
        result = await self.db.execute(
            select(Resume)
            .options(
                selectinload(Resume.experiences),
                selectinload(Resume.educations),
                selectinload(Resume.skills)
            )
            .where(Resume.id == resume_id)
        )
        resume = result.scalars().first()
        return resume

    async def delete_resume(self, resume_id: int) -> Resume:
        resume = await self.get_resume(resume_id)
        if not resume:
            return None
        await self.db.delete(resume)
        await self.db.commit()
        return resume
