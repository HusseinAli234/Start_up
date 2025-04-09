# resume_routes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.employers import JobPosting
from app.database import get_db
from app.services.vacancy_service import JobPostingService
from app.schemas.vacancy_schema import VacancyResponse
from typing import List
from sqlalchemy.orm import selectinload
from app.database import AsyncSessionLocal


router = APIRouter(prefix="/vacancy", tags=["Vacancy"])

@router.get("/", response_model=List[VacancyResponse])
async def get_all_vacancy(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(JobPosting)
        .options(
            selectinload(JobPosting.skills),
            selectinload(JobPosting.resumes)

        )
    )
    vacancies = result.scalars().all()
    return vacancies

@router.get("/{vacancy_id}", response_model=VacancyResponse)  # Указываем схему ответа
async def get_vacancy_by_id(vacancy_id: int, db: AsyncSession = Depends(get_db)):
    service = JobPostingService(db)
    vacancy = await service.get_job_posting(vacancy_id)
    if not vacancy:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    return vacancy


@router.delete("/{vacancy_id}")
async def delete_vacancy(vacancy_id: int, db: AsyncSession = Depends(get_db)):
    service = JobPostingService(db)
    if not await service.delete_job_posting(vacancy_id):
        raise HTTPException(status_code=404, detail="Vacancy not found")
    
    return {"message": "Vacancy deleted successfully"}



