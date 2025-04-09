
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.job_seekers import Resume, Education, Experience, Skill, TypeSkill
from app.schemas.resume_schema import ResumeCreate
from sqlalchemy.orm import selectinload
from sqlalchemy import delete
from app.models.employers import JobPosting
from fastapi import FastAPI, HTTPException

app = FastAPI()

items = {"foo": "The Foo Wrestlers"}


@app.get("/items/{item_id}")
async def read_item(item_id: str):
    if item_id not in items:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"item": items[item_id]}

class ResumeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_resume(self, resume_data: ResumeCreate, vacancy_id: int | None = None) -> Resume:
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

        if vacancy_id:
            # Если задан id вакансии, пытаемся получить вакансию
            job = await self.db.get(JobPosting, vacancy_id)
            if not job:
                raise HTTPException(status_code=404, detail="Vacancy not found")
            db_resume.job_postings.append(job)

        self.db.add(db_resume)
        await self.db.commit()  # асинхронный commit
        await self.db.refresh(db_resume)  # обновляем объект после сохранения
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
