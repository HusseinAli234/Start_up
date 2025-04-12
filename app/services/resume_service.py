
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.job_seekers import Resume, Education, Experience, Skill, TypeSkill
from app.schemas.resume_schema import ResumeCreate
from sqlalchemy.orm import selectinload
from sqlalchemy import delete
from app.models.employers import JobPosting
from fastapi import FastAPI, HTTPException
from app.users.models import User
from fastapi import status


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

    async def create_resume(self, resume_data: ResumeCreate, user: User, vacancy_id: int | None = None) -> Resume:
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
            ],
            user_id = user.id
        )

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

    async def resume_skill_add(self, resume_id: int, soft_skills: list[dict]):
        # Проверка на существование резюме
        result = await self.db.execute(select(Resume).where(Resume.id == resume_id))
        resume = result.scalar_one_or_none()

        if resume is None:
            raise ValueError(f"Resume with id {resume_id} not found")

        # Создание объектов ResumeSkill
        skills = []
        for skill in soft_skills:
            skill_obj = Skill(
                title=skill["title"],
                level=skill["level"],
                justification=skill["justification"],
                type=skill["type"],
                resume_id=resume_id
            )
            skills.append(skill_obj)

        # Добавление в сессию
        self.db.add_all(skills)
        await self.db.commit()

    async def get_resume(self, resume_id: int, user: User) -> Resume:
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
