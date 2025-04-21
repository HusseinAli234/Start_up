# resume_routes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.job_seekers import Resume
from app.database import get_db
from app.services.resume_service import ResumeService
from app.schemas.resume_schema import ResumeResponse
from typing import List
from sqlalchemy.orm import selectinload
from app.database import AsyncSessionLocal
from app.users.config import security, config, safe_get_current_subject
from app.users.models import User


router = APIRouter(prefix="/resumes", tags=["Resumes"])

@router.get("/", response_model=List[ResumeResponse])
async def get_all_resumes(db: AsyncSession = Depends(get_db), user: User = Depends(safe_get_current_subject)):
    result = await db.execute(
        select(Resume)
        .filter_by(user_id=user.id)
        .options(
            selectinload(Resume.skills),
            selectinload(Resume.educations),
            selectinload(Resume.experiences),
            selectinload(Resume.hard_total),
            selectinload(Resume.soft_total)
        )
    )
    resumes = result.scalars().all()
    return resumes

@router.get("/{resume_id}", response_model=ResumeResponse) 
async def get_resume_by_id(resume_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(safe_get_current_subject)):
    service = ResumeService(db)
    resume = await service.get_resume(resume_id, user)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    return resume

@router.get("/resumes_by_vacancy/{vacancy_id}",response_model=List[ResumeResponse])
async def save_test_result(vacancy_id:int,db:AsyncSession = Depends(get_db), user: User = Depends(safe_get_current_subject)):
    service = ResumeService(db)
    resume = await service.get_resumes_by_vacancy_sorted(vacancy_id, user)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    return resume



@router.delete("/{resume_id}")
async def delete_resume(resume_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(safe_get_current_subject)):
    service = ResumeService(db)
    if not await service.delete_resume(resume_id, user):
        raise HTTPException(status_code=404, detail="Resume not found")
    
    return {"message": "Resume deleted successfully"}



