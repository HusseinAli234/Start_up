# resume_routes.py
import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.job_seekers import Resume
from app.database import get_db
from app.services.resume_service import ResumeService
from app.services.cv_services import CVService
from app.schemas.resume_schema import ResumeResponse
from typing import List
from sqlalchemy.orm import selectinload
from app.database import AsyncSessionLocal
from app.users.config import security, config, safe_get_current_subject
from app.users.models import User
from datetime import datetime,timezone,timedelta
from sqlalchemy import desc

router = APIRouter(prefix="/resumes", tags=["Resumes"])

@router.get("/", response_model=List[ResumeResponse])
async def get_all_resumes(db: AsyncSession = Depends(get_db), user: User = Depends(safe_get_current_subject)):
    result = await db.execute(
        select(Resume)
        .filter_by(user_id=user.id)
        .order_by(desc(Resume.id))
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
@router.get("/count_resume")
async def count_resume(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(safe_get_current_subject)
):
    service = ResumeService(db)
    resume_count = await service.countResume(user)

    now = datetime.now(timezone.utc)
    expires_at = user.expires_at
    remaining_seconds = None
    if expires_at:
        delta = expires_at - now
        remaining_seconds = int(delta.total_seconds()) if delta.total_seconds() > 0 else 0

    return {
        "resume_count": resume_count,
        "remaining_seconds": remaining_seconds  # например, 7200 для 2 часов
    }

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

# @router.delete("/report/{resume_id}")
# async def delete_resume_report(resume_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(safe_get_current_subject)):
#     service = CVService(db)
  

#     if not await service.delete_report_from_gcs(resume_id,user):
#         raise HTTPException(status_code=404, detail="Resume Report not found")
    
#     return {"message": "Resume report deleted successfully"}

