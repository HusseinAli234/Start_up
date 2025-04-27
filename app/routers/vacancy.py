# resume_routes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.employers import JobPosting
from app.database import get_db
from app.services.vacancy_service import JobPostingService
from app.schemas.vacancy_schema import VacancyResponse,SortResumesResponse
from typing import List
from sqlalchemy.orm import selectinload
from app.users.config import security, config, safe_get_current_subject
from app.users.models import User



router = APIRouter(prefix="/vacancy", tags=["Vacancy"])
    

@router.get("/", response_model=List[VacancyResponse])
async def get_all_vacancy(db: AsyncSession = Depends(get_db), user: User = Depends(safe_get_current_subject)):
    result = await db.execute(
        select(JobPosting)
        .filter_by(user_id=user.id)
        .options(
            selectinload(JobPosting.skills),
            selectinload(JobPosting.resumes)

        )
    )
    vacancies = result.scalars().all()
    return vacancies

@router.get("/{vacancy_id}", response_model=VacancyResponse)
async def get_vacancy_by_id(vacancy_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(safe_get_current_subject)):
    service = JobPostingService(db)
    vacancy = await service.get_job_posting(vacancy_id, user)
    if not vacancy:
        raise HTTPException(status_code=404, detail="Вакансия не найдена или у вас нет доступа к ней")
    return vacancy



@router.delete("/{vacancy_id}")
async def delete_vacancy(vacancy_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(safe_get_current_subject)):
    service = JobPostingService(db)
    if not await service.delete_job_posting(vacancy_id, user):  # Передаем user сюда
        raise HTTPException(status_code=404, detail="Vacancy not found or you don't have permission to delete it")
    
    return {"message": "Vacancy deleted successfully"}


# @router.get("/sort/{vacancy_id}",response_model=List[SortResumesResponse])
# async def sort_resumes(vacancy_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(safe_get_current_subject)):
#     service = JobPostingService(db)
#     resumes = await service.sort_by_hard(vacancy_id, user)
#     if not resumes:
#         raise HTTPException(status_code=404, detail="Resumes didn't upload")
#     return resumes


